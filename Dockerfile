FROM python:3.9-alpine

RUN apk add libxml2-dev g++ gcc libxslt-dev

COPY requirements.txt /
RUN pip install -r /requirements.txt

ENV BJ_USERNAME username
ENV BJ_PASSWORD password

COPY app/ /app
WORKDIR /app

EXPOSE 8080

CMD ["python", "app.py"]