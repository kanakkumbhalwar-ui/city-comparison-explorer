from flask import Flask, render_template, request
import requests

app = Flask(__name__)


def get_city_data(city_name):
    try:
        # City search
        search_url = "https://geocoding-api.open-meteo.com/v1/search"

        search_params = {
            "name": city_name,
            "count": 1,
            "language": "en",
            "format": "json"
        }

        response = requests.get(
            search_url,
            params=search_params,
            timeout=10
        )

        response.raise_for_status()
        data = response.json()

        if "results" not in data or not data["results"]:
            return None

        city = data["results"][0]

        latitude = city.get("latitude")
        longitude = city.get("longitude")

        # Weather data
        weather_url = "https://api.open-meteo.com/v1/forecast"

        weather_params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
            "timezone": "auto"
        }

        weather_response = requests.get(
            weather_url,
            params=weather_params,
            timeout=10
        )

        weather_response.raise_for_status()

        weather_data = weather_response.json()
        current = weather_data.get("current", {})

        return {
            "name": city.get("name", "Unknown"),
            "country": city.get("country", "Unknown"),
            "country_code": city.get("country_code", ""),
            "population": city.get("population"),

            "latitude": latitude,
            "longitude": longitude,

            "timezone": city.get(
                "timezone",
                "Unknown"
            ),

            "temperature": current.get(
                "temperature_2m"
            ),

            "humidity": current.get(
                "relative_humidity_2m"
            ),

            "wind": current.get(
                "wind_speed_10m"
            )
        }

    except Exception as e:

        print("Error:", e)

        return None


def compare_cities(city1, city2):

    comparison = []

    parameters = [
        ("Temperature", "temperature"),
        ("Humidity", "humidity"),
        ("Wind Speed", "wind"),
        ("Population", "population")
    ]

    for label, key in parameters:

        value1 = city1.get(key)
        value2 = city2.get(key)

        if (
            isinstance(value1, (int, float))
            and isinstance(value2, (int, float))
        ):

            difference = abs(
                value1 - value2
            )

            if key == "population":
                difference = int(
                    round(difference)
                )
            else:
                difference = round(
                    difference,
                    2
                )

            comparison.append({
                "parameter": label,
                "city1": value1,
                "city2": value2,
                "difference": difference
            })

    return comparison


@app.route("/")
def home():

    return render_template(
        "index.html",
        city1=None,
        city2=None,
        comparison=None,
        error=None
    )


@app.route(
    "/compare",
    methods=["GET"]
)
def compare_page():

    return render_template(
        "index.html",
        city1=None,
        city2=None,
        comparison=None,
        error=None
    )


@app.route(
    "/compare",
    methods=["POST"]
)
def compare():

    city1_name = request.form.get(
        "city1",
        ""
    ).strip()

    city2_name = request.form.get(
        "city2",
        ""
    ).strip()

    if not city1_name or not city2_name:

        return render_template(
            "index.html",
            city1=None,
            city2=None,
            comparison=None,
            error="Please enter both city names."
        )

    city1 = get_city_data(
        city1_name
    )

    city2 = get_city_data(
        city2_name
    )

    if city1 is None:

        return render_template(
            "index.html",
            city1=None,
            city2=None,
            comparison=None,
            error=f"Could not find city: {city1_name}"
        )

    if city2 is None:

        return render_template(
            "index.html",
            city1=None,
            city2=None,
            comparison=None,
            error=f"Could not find city: {city2_name}"
        )

    comparison = compare_cities(
        city1,
        city2
    )

    return render_template(
        "index.html",
        city1=city1,
        city2=city2,
        comparison=comparison,
        error=None
    )


if __name__ == "__main__":

    app.run(
        debug=True
    )