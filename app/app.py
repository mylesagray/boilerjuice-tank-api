import requests
import time
from os import environ
from lxml import html
from flask import Response, Flask
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from prometheus_client import Gauge, generate_latest, make_wsgi_app

# Import variables from environment
if environ.get('BJ_USERNAME') != "username":
    USERNAME = environ.get('BJ_USERNAME')
else:
    raise Exception("Please set the username in the environment variables.")

if environ.get('BJ_PASSWORD') != "password":
    PASSWORD = environ.get('BJ_PASSWORD')
else:
    raise Exception("Please set the password in the environment variables.")

LOGIN_URL = "https://www.boilerjuice.com/login/"
URL = "https://www.boilerjuice.com/my-tank/"

app = Flask(__name__)
@app.route('/', methods=['GET'])
def main():
    try:
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
        result = session_requests.post(LOGIN_URL, data = payload, headers = dict(referer = LOGIN_URL))

        # Scrape url
        result = session_requests.get(URL, headers = dict(referer = URL))
        tree = html.fromstring(result.content)
        tank_level = tree.xpath("//div[@class='jerryCan']/div/p/text()")
        tank_capacity = tree.xpath("//input[@title='tank-size-count']/@value")
        tank_level_name = tree.xpath(
            "//div[@class='bar-container']/div[@class='status']/p/text()")

        bj_data = {}
        for level in tank_level:
            if "litres" in level:
                # remove parenthesis
                level = level.replace("(", "")
                level = level.replace(")", "")
                level = level.replace("litres", "")
                level = level.strip()
                bj_data["level"] = int(level)
            else:
                percent = level
                bj_data["percent"] = percent

        data = {"litres": bj_data["level"], "percent": bj_data["percent"], "capacity": tank_capacity[0], "level_name": tank_level_name[0]}
        return(data)

    except:
        print("Unable to connect to boilerjuice.com")

def metrics():
    while True:
        try:
            bj_data = main()

            # Create Gauge object
            bj_level = Gauge('bj_level', 'BoilerJuice tank level', ['litres', 'percent', 'capacity', 'level_name'])
            bj_level.labels(litres=bj_data["litres"], percent=bj_data["percent"], capacity=bj_data["capacity"], level_name=bj_data["level_name"])
            data = generate_latest(bj_level)

            return Response(data, mimetype="text/plain")
        except:
            print("Unable to create prometheus metrics")
        time.sleep(60)


# Add prometheus wsgi middleware to route /metrics requests
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    '/metrics': make_wsgi_app()
})
metrics()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
