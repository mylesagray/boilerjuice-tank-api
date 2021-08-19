import requests
from os import environ
from lxml import html
from flask import Response, Flask
from prometheus_client import Gauge, generate_latest

# Import variables from environment
if environ.get('BJ_USERNAME') != "username":
    USERNAME = environ.get('BJ_USERNAME')
else:
    raise Exception("Please set the username in the environment variables.")

if environ.get('BJ_PASSWORD') != "password":
    PASSWORD = environ.get('BJ_PASSWORD')
else:
    raise Exception("Please set the password in the environment variables.")

# Specify login and target URLs for BoilerJuice
LOGIN_URL = "https://www.boilerjuice.com/login/"
URL = "https://www.boilerjuice.com/my-tank/"

# Create Prometheus Gauge objects
oil_level_litres = Gauge(
    'oil_level_litres', 'BoilerJuice tank level in Litres', ['email', 'level_name'])
oil_level_percent = Gauge(
    'oil_level_percent', 'BoilerJuice tank level percentage full', ['email', 'level_name'])
oil_level_capacity = Gauge(
    'oil_level_capacity', 'BoilerJuice tank capacity in Litres', ['email'])

session = None

# Login to BoilerJuice
def login():
    try:
        # Create a session, and use for all future requests
        session_requests = requests.session()

        # Get login csrf token
        result = session_requests.get(LOGIN_URL)
        tree = html.fromstring(result.text)

        # Create payload
        payload = {
            "username": USERNAME,
            "password": PASSWORD
        }

        # Perform login
        result = session_requests.post(
            LOGIN_URL, data=payload, headers=dict(referer=LOGIN_URL))
        
        if 'jwt' in session_requests.cookies:
            print("Login successful")
        else:
            print("Login failed")
            exit()

        return session_requests
    except Exception as e:
        print(e)

SESH = None

app = Flask(__name__)
@app.route('/', methods=['GET'])
def main():
    try:
        global SESH
        # Scrape url
        if SESH == None or 'jwt' not in SESH.cookies:
            SESH = login()
        
        if 'jwt' in SESH.cookies:
            result = SESH.get(URL, headers=dict(referer=URL))

            tree = html.fromstring(result.content)
            tank_level = tree.xpath("//div[@class='jerryCan']/div/p/text()")
            tank_capacity = tree.xpath(
                "//input[@title='tank-size-count']/@value")
            tank_level_name = tree.xpath(
                "//div[@class='bar-container']/div[@class='status']/p/text()")

            # Create object to store scraped data in
            bj_data = {}

            # Find the oil level
            for level in tank_level:
                # In litres
                if "litres" in level:
                    # remove parenthesis
                    level = level.replace("(", "")
                    level = level.replace(")", "")
                    level = level.replace("litres", "")
                    level = level.strip()
                    bj_data["level"] = int(level)
                # In percentage
                else:
                    percent = level
                    bj_data["percent"] = percent

            # Populate data object
            data = {"litres": bj_data["level"], "percent": bj_data["percent"],
                    "capacity": tank_capacity[0], "level_name": tank_level_name[0]}

            # Return API result
            return(data)

    except Exception as e:
        print("Unable to connect to boilerjuice.com", e)


@app.route('/metrics', methods=['GET'])
def metrics():
    try:
        # Pull back latest metrics from API
        bj_data = main()

        # Populate Prometheus Gauge objects with new data
        oil_level_litres.labels(
            email=USERNAME, level_name=bj_data["level_name"]).set(bj_data["litres"])

        oil_level_percent.labels(
            email=USERNAME, level_name=bj_data["level_name"]).set(bj_data["percent"])

        oil_level_capacity.labels(
            email=USERNAME).set(bj_data["capacity"])

        # Return Prometheus metrics
        return Response(generate_latest(), mimetype="text/plain")
    except Exception as e:
        print("Unable to create prometheus metrics:", e)

if __name__ == '__main__':
    app.debug=False
    app.run(host='0.0.0.0', port=8080)
