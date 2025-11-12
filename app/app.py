"""
Module provides a JSON API for querying information from BoilerJuice website
"""
from os import environ
import sys
import re
import requests
from lxml import html
from flask import Response, Flask
from prometheus_client import Gauge, Enum, generate_latest

# Import variables from environment
if environ.get('BJ_USERNAME') != "username":
    USERNAME = environ.get('BJ_USERNAME')
else:
    raise Exception("Please set the username in the environment variables.")

if environ.get('BJ_PASSWORD') != "password":
    PASSWORD = environ.get('BJ_PASSWORD')
else:
    raise Exception("Please set the password in the environment variables.")

if environ.get('TANK_ID') != "id" and environ.get('TANK_ID') != "":
    TANK = environ.get('TANK_ID')
else:
    raise Exception("Please set the tank ID in the environment variables.")

# Specify login and target URLs for BoilerJuice
LOGIN_URL = "https://www.boilerjuice.com/uk/users/login"
URL = "https://www.boilerjuice.com/uk/users/tanks/"

# Create Prometheus Gauge objects
oil_level_litres = Gauge(
    'oil_level_litres', 'BoilerJuice tank level in Litres', ['email'])
oil_level_total_litres = Gauge(
    'oil_level_total_litres', 'BoilerJuice tank total level in Litres', ['email'])
oil_level_percent = Gauge(
    'oil_level_percent', 'BoilerJuice tank level percentage full', ['email'])
oil_level_total_percent = Gauge(
    'oil_level_total_percent', 'BoilerJuice tank total level percentage full', ['email'])
oil_level_capacity = Gauge(
    'oil_level_capacity', 'BoilerJuice tank capacity in Litres', ['email'])
oil_level_name = Enum(
    'oil_level_name', 'BoilerJuice tank level name', ['email'], states=['High', 'Medium', 'Low'])


def login():
    """
    Logs into BoilerJuice website and populates the session key
    """
    try:
        # Create a session, and use for all future requests
        session = requests.session()

        # Get login csrf token
        result = session.get(LOGIN_URL)
        tree = html.fromstring(result.text)
        authenticity_token = list(
            set(tree.xpath("//input[@name='authenticity_token']/@value")))[0]

        # Create payload
        payload = {
            "user[email]": USERNAME,
            "user[password]": PASSWORD,
            "authenticity_token": authenticity_token,
            "commit": "Log in"
        }

        # Perform login
        result = session.post(
            LOGIN_URL, data=payload, headers=dict(referer=LOGIN_URL))

        if 'jwt' in session.cookies:
            print("Login successful")
        else:
            print("Login failed")
            sys.exit()

        return session

    except Exception as err:
        print(err)
        raise


SESH = None

app = Flask(__name__)


@app.route('/', methods=['GET'])
def main():
    """
    Retrieves tank information and builds
    a JSON object for API return
    """
    try:
        global SESH
        # Scrape url
        if SESH is None or 'jwt' not in SESH.cookies:
            SESH = login()

        if 'jwt' in SESH.cookies:
            result = SESH.get(URL + TANK + '/edit', headers=dict(referer=URL))

            tree = html.fromstring(result.content)
            tank_level = tree.xpath(
                "//div[contains(@id, 'usable-oil')]/div/p/text()")
            tank_total_level = tree.xpath(
                "//div[contains(@id, 'total-oil')]/div/p/text()")
            tank_capacity = tree.xpath(
                "//input[@title='tank-size-count']/@value")
            tank_level_name = tree.xpath(
                "//div[@class='bar-container']/div[@class='status']/p/text()")
            tank_percentage = tree.xpath(
                "//div[contains(@id, 'usable-oil')]//div/@data-percentage")
            tank_total_percentage = tree.xpath(
                "//div[contains(@id, 'total-oil')]//div/@data-percentage"
            )

            # Create object to store scraped data in
            bj_data = {}

            # --- Fixed parsing for usable oil level ---
            for level in tank_level:
                if "litres" in level:
                    match = re.search(r"(\d+(?:\.\d+)?)", level)
                    if match:
                        bj_data["level"] = float(match.group(1))

            # --- Fixed parsing for total oil level ---
            for level in tank_total_level:
                if "litres" in level:
                    match = re.search(r"(\d+(?:\.\d+)?)", level)
                    if match:
                        bj_data["total_level"] = float(match.group(1))

            # Percentages and capacity
            bj_data["percent"] = float(tank_percentage[0]) if tank_percentage else 0.0
            bj_data["total_percent"] = float(tank_total_percentage[0]) if tank_total_percentage else 0.0

            # Populate data object
            data = {
                "litres": bj_data.get("level", 0.0),
                "total_litres": bj_data.get("total_level", 0.0),
                "percent": bj_data.get("percent", 0.0),
                "total_percent": bj_data.get("total_percent", 0.0),
                "capacity": float(tank_capacity[0]) if tank_capacity else 0.0
            }

            if tank_level_name:
                data["level_name"] = tank_level_name[0]

            # Return API result
            return data

    except Exception as err:
        print("Unable to connect to boilerjuice.com", err)
        raise


@app.route('/metrics', methods=['GET'])
def metrics():
    """
    Prometheus metric endpoint build and export
    """
    try:
        # Pull back latest metrics from API
        bj_data = main()

        # Populate Prometheus Gauge objects with new data
        oil_level_litres.labels(email=USERNAME).set(bj_data["litres"])
        oil_level_total_litres.labels(email=USERNAME).set(bj_data["total_litres"])
        oil_level_percent.labels(email=USERNAME).set(bj_data["percent"])
        oil_level_total_percent.labels(email=USERNAME).set(bj_data["total_percent"])
        oil_level_capacity.labels(email=USERNAME).set(bj_data["capacity"])

        if "level_name" in bj_data:
            oil_level_name.labels(email=USERNAME).state(bj_data["level_name"])

        # Return Prometheus metrics
        return Response(generate_latest(), mimetype="text/plain")

    except Exception as err:
        print("Unable to create prometheus metrics:", err)
        raise


if __name__ == '__main__':
    app.debug = False
    app.run(host='0.0.0.0', port=8080)
