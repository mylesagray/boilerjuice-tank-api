FROM python:3.13-alpine@sha256:9b4929a72599b6c6389ece4ecbf415fd1355129f22bb92bb137eea098f05e975 as base

LABEL org.opencontainers.image.authors="Myles Gray"
LABEL org.opencontainers.image.source='https://github.com/mylesagray/boilerjuice-tank-api'
LABEL org.opencontainers.image.url='https://github.com/mylesagray/boilerjuice-tank-api'
LABEL org.opencontainers.image.documentation='https://github.com/mylesagray/boilerjuice-tank-api'

# Setup env
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONFAULTHANDLER 1

FROM base AS python-deps

# Install pipenv and compilation dependencies
RUN python -m pip install pipenv
RUN apk add libxml2-dev g++ gcc libxslt-dev

# Install python dependencies in /.venv
COPY Pipfile .
COPY Pipfile.lock .
RUN PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy

FROM base AS runtime

# Copy virtual env from python-deps stage
COPY --from=python-deps /.venv /.venv
ENV PATH="/.venv/bin:$PATH"

# Create and switch to a new user
RUN adduser -S appuser
WORKDIR /home/appuser
USER appuser

# Import Env vars for config
ENV BJ_USERNAME username
ENV BJ_PASSWORD password
ENV TANK_ID id

# Install application into container
COPY app/ .

EXPOSE 8080

CMD ["python", "app.py"]
