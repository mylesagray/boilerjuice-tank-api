# Boilerjuice Scraping API

## Intro

Boilerjuice.com has public API, and pages are rendered via PHP with data pre-baked, as a result - to get information back from the site about your Oil Tank's current level you need to auth with the site and scrape the data back from the web pages.

That is what this project does.

## Function

Example input page:

![My Tank page](img/my-tank.png)

Example API output:

```json
{
  "capacity": "1000",
  "level_name": "High",
  "litres": "750",
  "percent": "75"
}
```

## Run

Run the API:

```sh
docker run -d -p 8080:8080 -e BJ_USERNAME=my@emailaddress.com -e BJ_PASSWORD=password ghcr.io/mylesagray/boilerjuice-tank
```

Docker images are available on DockerHub or GitHub Container Registry:

```sh
ghcr.io/mylesagray/boilerjuice-tank
mylesagray/boilerjuice-tank
```

## Use

Access the API:

```sh
[open localhost:8080](http://localhost:8080)
```
