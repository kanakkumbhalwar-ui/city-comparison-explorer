from flask import Flask, render_template, request
import requests
import time

app = Flask(__name__)

CITY_CACHE = {}
CACHE_DURATION = 600

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


def get_city_data(city):
    city = (city or "").strip()

    if not city:
        return None, "Please enter a city name."

    cache_key = city.lower()
    now = time.time()

    cached = CITY_CACHE.get(cache_key)
    if cached and now - cached["time"] < CACHE_DURATION:
        return cached["data"], None

    try:
        geo_response = requests.get(
            GEOCODING_URL,
            params={
                "name": city,
                "count": 1,
                "language": "en",
                "format": "json"
            },
            timeout=15
        )

        if geo_response.status_code == 429:
            return None, "Weather service is busy. Please wait a minute and try again."

        geo_response.raise_for_status()
        results = geo_response.json().get("results", [])

        if not results:
            return None, f"Could not find city: {city}"

        place = results[0]

        weather_response = requests.get(
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

        if weather_response.status_code == 429:
            return None, "Weather service is busy. Please wait a minute and try again."

        weather_response.raise_for_status()
        weather_json = weather_response.json()
        current = weather_json.get("current", {})

        data = {
            "name": place.get("name", city),
            "city": place.get("name", city),
            "country": place.get("country", ""),
            "country_code": place.get("country_code", ""),
            "latitude": place.get("latitude", 0),
            "longitude": place.get("longitude", 0),
            "timezone": weather_json.get("timezone", ""),
            "temperature": current.get("temperature_2m", 0),
            "humidity": current.get("relative_humidity_2m", 0),
            "wind": current.get("wind_speed_10m", 0),
            "population": None
        }

        CITY_CACHE[cache_key] = {
            "time": now,
            "data": data
        }

        return data, None

    except requests.RequestException as error:
        app.logger.error("API REQUEST ERROR: %s", error)
        return None, "Weather service is temporarily unavailable. Please try again shortly."

    except (ValueError, KeyError, TypeError) as error:
        app.logger.error("DATA PROCESSING ERROR: %s", error)
        return None, "Weather data could not be processed. Please try again."


def make_comparison(city1, city2):
    comparison = []

    parameters = [
        ("Temperature", "temperature"),
        ("Humidity", "humidity"),
        ("Wind Speed", "wind")
    ]

    for label, key in parameters:
        value1 = float(city1.get(key) or 0)
        value2 = float(city2.get(key) or 0)

        comparison.append({
            "parameter": label,
            "city1": value1,
            "city2": value2,
            "difference": round(abs(value1 - value2), 2)
        })

    return comparison


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/compare", methods=["POST"])
def compare():
    city_name1 = request.form.get("city1", "").strip()
    city_name2 = request.form.get("city2", "").strip()

    data1, error1 = get_city_data(city_name1)
    if error1:
        return render_template(
            "index.html",
            error=error1,
            city1=city_name1,
            city2=city_name2
        )

    data2, error2 = get_city_data(city_name2)
    if error2:
        return render_template(
            "index.html",
            error=error2,
            city1=city_name1,
            city2=city_name2
        )

    comparison = make_comparison(data1, data2)

    return render_template(
        "index.html",
        city1=data1,
        city2=data2,
        comparison=comparison
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
