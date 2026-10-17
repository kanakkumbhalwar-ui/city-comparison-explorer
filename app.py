
from flask import Flask, render_template, request
import requests
import time

app = Flask(__name__)

CITY_CACHE = {}
CACHE_DURATION = 600

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

# City population data: Census 2011, city proper figures.
# Figures are not current population estimates.
POPULATION_DATA = {
    "mumbai": 12442373,
    "pune": 3124458,
    "nagpur": 2405665,
    "nashik": 1486053,
    "jaipur": 3046163,
    "ahmedabad": 5570585,
    "hyderabad": 6731790,
    "chennai": 4646732,
    "kolkata": 4496694,
    "delhi": 11034555,
    "bengaluru": 8443675,
    "surat": 4462002
}

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Dense drizzle",
    61: "Light rain",
    63: "Moderate rain",
    65: "Heavy rain",
    80: "Rain showers",
    81: "Moderate rain showers",
    82: "Heavy rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with heavy hail"
}


def get_city_data(city):
    city = (city or "").strip()

    if not city:
        return None, "Please enter a city name."

    key = city.casefold()
    now = time.time()

    cached = CITY_CACHE.get(key)
    if cached and now - cached["time"] < CACHE_DURATION:
        return cached["data"], None

    try:
        geo = requests.get(
            GEOCODING_URL,
            params={
                "name": city,
                "count": 10,
                "language": "en",
                "format": "json"
            },
            timeout=15
        )
        geo.raise_for_status()

        results = geo.json().get("results") or []

        if not results:
            app.logger.warning("City not found: %s", city)
            return None, f"City not found: {city}. Check the spelling."

        # Prefer a result matching the entered city name.
        place = next(
            (
                item for item in results
                if item.get("name", "").casefold() == city.casefold()
            ),
            results[0]
        )

        weather = requests.get(
            WEATHER_URL,
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": (
                    "temperature_2m,relative_humidity_2m,"
                    "wind_speed_10m,apparent_temperature,"
                    "precipitation,weather_code"
                ),
                "timezone": "auto",
                "forecast_days": 5
            },
            timeout=20
        )
        weather.raise_for_status()

        weather_data = weather.json()
        current = weather_data.get("current") or {}

        if not current:
            app.logger.warning("No current weather returned for %s", city)
            return None, f"Weather data unavailable for {city}. Try again later."

        code = current.get("weather_code")
        resolved_name = place.get("name", city)

        # Population is available only for cities in this reference dataset.
        population = POPULATION_DATA.get(resolved_name.casefold())

        data = {
            "name": resolved_name,
            "city": resolved_name,
            "country": place.get("country", ""),
            "country_code": place.get("country_code", ""),
            "latitude": place.get("latitude"),
            "longitude": place.get("longitude"),
            "timezone": weather_data.get("timezone", "Unknown"),
            "temperature": current.get("temperature_2m"),
            "feels_like": current.get("apparent_temperature"),
            "humidity": current.get("relative_humidity_2m"),
            "wind": current.get("wind_speed_10m"),
            "precipitation": current.get("precipitation"),
            "weather_description": WEATHER_CODES.get(
                code, "Weather information unavailable"
            ),
            "population": population,
            "population_year": 2011 if population is not None else None
        }

        CITY_CACHE[key] = {"time": now, "data": data}
        return data, None

    except requests.HTTPError as error:
        status = error.response.status_code if error.response is not None else None
        app.logger.warning("HTTP error for %s: %s", city, status)

        if status == 429:
            return None, "Weather service is busy. Please wait a minute and try again."

        return None, f"Weather provider returned an error for {city}. Please try again."

    except requests.Timeout:
        app.logger.warning("Request timed out for city: %s", city)
        return None, "The weather service took too long to respond. Please try again."

    except requests.RequestException:
        app.logger.exception("Network/API request failed for city: %s", city)
        return None, "Could not connect to the weather service. Please try again."

    except (ValueError, KeyError, TypeError):
        app.logger.exception("Data processing failed for city: %s", city)
        return None, "Weather data could not be processed. Please try again."


def number(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def make_comparison(city1, city2):
    rows = []

    parameters = [
        ("Temperature", "temperature", "°C"),
        ("Humidity", "humidity", "%"),
        ("Wind Speed", "wind", "km/h"),
        ("Feels Like", "feels_like", "°C"),
        ("Precipitation", "precipitation", "mm"),
        ("Population (Census 2011)", "population", "people")
    ]

    for label, key, unit in parameters:
        a = number(city1.get(key))
        b = number(city2.get(key))

        if a is None or b is None:
            # Don't compare missing population or weather values as zero.
            continue

        rows.append({
            "parameter": label,
            "city1": int(a) if key == "population" else round(a, 1),
            "city2": int(b) if key == "population" else round(b, 1),
            "difference": (
                int(abs(a - b))
                if key == "population"
                else round(abs(a - b), 1)
            ),
            "unit": unit
        })

    return rows


def make_insights(city1, city2):
    insights = []

    parameters = [
        ("🌡️", "Temperature", "temperature", "°C"),
        ("💧", "Humidity", "humidity", "%"),
        ("💨", "Wind Speed", "wind", "km/h"),
        ("🌧️", "Precipitation", "precipitation", "mm"),
        ("👥", "Population (Census 2011)", "population", "people")
    ]

    for icon, label, key, unit in parameters:
        a = number(city1.get(key))
        b = number(city2.get(key))

        if a is None or b is None:
            continue

        difference = abs(a - b)

        if difference < 0.05:
            message = f"{label} is almost the same in both cities."
        elif a > b:
            message = (
                f"{city1['name']} has a higher {label.lower()} "
                f"than {city2['name']} by {difference:,.1f} {unit}."
            )
        else:
            message = (
                f"{city2['name']} has a higher {label.lower()} "
                f"than {city1['name']} by {difference:,.1f} {unit}."
            )

        insights.append({
            "icon": icon,
            "title": label,
            "text": message
        })

    return insights


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/compare", methods=["GET", "POST"])
def compare():
    if request.method == "GET":
        return render_template("index.html")

    name1 = request.form.get("city1", "").strip()
    name2 = request.form.get("city2", "").strip()

    if not name1 or not name2:
        return render_template(
            "index.html",
            error="Please enter both city names.",
            city_input1=name1,
            city_input2=name2
        )

    if name1.casefold() == name2.casefold():
        return render_template(
            "index.html",
            error="Please enter two different cities.",
            city_input1=name1,
            city_input2=name2
        )

    city1, error = get_city_data(name1)
    if error:
        return render_template(
            "index.html",
            error=error,
            city_input1=name1,
            city_input2=name2
        )

    city2, error = get_city_data(name2)
    if error:
        return render_template(
            "index.html",
            error=error,
            city_input1=name1,
            city_input2=name2
        )

    return render_template(
        "index.html",
        city1=city1,
        city2=city2,
        comparison=make_comparison(city1, city2),
        insights=make_insights(city1, city2)
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
