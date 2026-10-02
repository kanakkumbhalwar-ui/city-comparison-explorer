from flask import Flask, render_template, request
import requests

app = Flask(__name__)


# -----------------------------------
# GET CITY WEATHER DATA
# -----------------------------------
def get_city_data(city_name):
    try:
        city_name = city_name.strip()

        if not city_name:
            return None

        # -----------------------------------
        # 1. CITY SEARCH
        # -----------------------------------
        search_url = "https://geocoding-api.open-meteo.com/v1/search"

        search_params = {
            "name": city_name,
            "count": 10,
            "language": "en",
            "format": "json"
        }

        response = requests.get(
            search_url,
            params=search_params,
            timeout=15,
            headers={
                "User-Agent": "City-Comparison-Explorer/1.0"
            }
        )

        print("City Search Status:", response.status_code)
        print("City Search URL:", response.url)

        response.raise_for_status()

        data = response.json()

        print("City Search Response:", data)

        results = data.get("results", [])

        if not results:
            return None

        # -----------------------------------
        # 2. SELECT BEST CITY RESULT
        # -----------------------------------
        city = None

        # First try exact city-name match
        for result in results:
            if result.get("name", "").lower() == city_name.lower():
                city = result
                break

        # Otherwise use first result
        if city is None:
            city = results[0]

        latitude = city.get("latitude")
        longitude = city.get("longitude")

        if latitude is None or longitude is None:
            return None

        # -----------------------------------
        # 3. WEATHER DATA
        # -----------------------------------
        weather_url = "https://api.open-meteo.com/v1/forecast"

        weather_params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": (
                "temperature_2m,"
                "relative_humidity_2m,"
                "wind_speed_10m"
            ),
            "timezone": "auto"
        }

        weather_response = requests.get(
            weather_url,
            params=weather_params,
            timeout=15,
            headers={
                "User-Agent": "City-Comparison-Explorer/1.0"
            }
        )

        print("Weather Status:", weather_response.status_code)
        print("Weather URL:", weather_response.url)

        weather_response.raise_for_status()

        weather_data = weather_response.json()

        print("Weather Response:", weather_data)

        current = weather_data.get("current", {})

        # -----------------------------------
        # 4. RETURN CITY DATA
        # -----------------------------------
        return {
            "name": city.get("name", "Unknown"),

            "country": city.get(
                "country",
                "Unknown"
            ),

            "country_code": city.get(
                "country_code",
                ""
            ),

            "population": city.get(
                "population"
            ),

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

    except requests.exceptions.RequestException as e:

        print("API Request Error:", e)

        return None

    except Exception as e:

        print("General Error:", e)

        return None


# -----------------------------------
# COMPARE CITIES
# -----------------------------------
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


# -----------------------------------
# HOME PAGE
# -----------------------------------
@app.route("/")
def home():

    return render_template(
        "index.html",
        city1=None,
        city2=None,
        comparison=None,
        error=None
    )


# -----------------------------------
# COMPARE PAGE - GET
# -----------------------------------
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


# -----------------------------------
# COMPARE CITIES - POST
# -----------------------------------
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

    # Empty city check
    if not city1_name or not city2_name:

        return render_template(
            "index.html",
            city1=None,
            city2=None,
            comparison=None,
            error="Please enter both city names."
        )

    # Get city 1
    city1 = get_city_data(
        city1_name
    )

    # Get city 2
    city2 = get_city_data(
        city2_name
    )

    # City 1 error
    if city1 is None:

        return render_template(
            "index.html",
            city1=None,
            city2=None,
            comparison=None,
            error=(
                f"Could not find city: "
                f"{city1_name}. "
                f"Please check the city name."
            )
        )

    # City 2 error
    if city2 is None:

        return render_template(
            "index.html",
            city1=None,
            city2=None,
            comparison=None,
            error=(
                f"Could not find city: "
                f"{city2_name}. "
                f"Please check the city name."
            )
        )

    # Compare
    comparison = compare_cities(
        city1,
        city2
    )

    # Show result
    return render_template(
        "index.html",
        city1=city1,
        city2=city2,
        comparison=comparison,
        error=None
    )


# -----------------------------------
# RUN APPLICATION
# -----------------------------------
if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
