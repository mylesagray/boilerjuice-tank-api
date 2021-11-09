import requests
from os import environ
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
oil_level_percent = Gauge(
    'oil_level_percent', 'BoilerJuice tank level percentage full', ['email'])
oil_level_capacity = Gauge(
    'oil_level_capacity', 'BoilerJuice tank capacity in Litres', ['email'])
oil_level_name = Enum(
    'oil_level_name', 'BoilerJuice tank level name', ['email'], states=['High', 'Medium', 'Low'])

session = None

# Login to BoilerJuice
def login():
    try:
        # Create a session, and use for all future requests
        session_requests = requests.session()

        # Get login csrf token
        result = session_requests.get(LOGIN_URL)
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
            result = SESH.get(URL+TANK+'/edit', headers=dict(referer=URL))

            tree = html.fromstring(result.content)
            tank_level = tree.xpath(
                "//div[contains(@class, 'jerryCan')]/div/p/text()")
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
                    bj_data["level"] = float(level)
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
            email=USERNAME).set(bj_data["litres"])

        oil_level_percent.labels(
            email=USERNAME).set(bj_data["percent"])

        oil_level_capacity.labels(
            email=USERNAME).set(bj_data["capacity"])
        
        oil_level_name.labels(
            email=USERNAME).state(bj_data["level_name"])

        # Return Prometheus metrics
        return Response(generate_latest(), mimetype="text/plain")
    except Exception as e:
        print("Unable to create prometheus metrics:", e)

if __name__ == '__main__':
    app.debug=True
    app.run(host='0.0.0.0', port=8080)
