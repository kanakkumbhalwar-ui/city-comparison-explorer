from flask import Flask, render_template, request
import requests
import time

app = Flask(__name__)

# Cache weather data for 10 minutes to reduce API requests
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
                    "apparent_temperature,is_day,precipitation,"
                    "weather_code,wind_speed_10m"
                ),
                "daily": (
                    "weather_code,temperature_2m_max,"
                    "temperature_2m_min"
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

        data = {
            "city": place.get("name", city),
            "country": place.get("country", ""),
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": weather_json.get("current", {}),
            "daily": weather_json.get("daily", {}),
            "timezone": weather_json.get("timezone", "")
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


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/compare", methods=["POST"])
def compare():
    city1 = request.form.get("city1", "").strip()
    city2 = request.form.get("city2", "").strip()

    data1, error1 = get_city_data(city1)
    data2, error2 = get_city_data(city2)

    if error1 or error2:
        return render_template(
            "index.html",
            error=error1 or error2,
            city1=city1,
            city2=city2
        )

    return render_template(
        "index.html",
        data1=data1,
        data2=data2,
        city1=city1,
        city2=city2
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
