import requests
from os import environ
from lxml import html
from flask import Flask

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
                bj_data["level"] = level
            else:
                percent = level
                bj_data["percent"] = percent

        data = {"litres": bj_data["level"], "percent": bj_data["percent"], "capacity": tank_capacity[0], "level_name": tank_level_name[0]}
        return(data)

    except:
        print("Unable to connect to boilerjuice.com")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
