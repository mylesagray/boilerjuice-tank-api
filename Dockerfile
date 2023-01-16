FROM python:3.10-alpine@sha256:ef5536e8f22c1697807cabe68765567cea4558b4b3f3287e2277b336cf2273a5 as base

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
