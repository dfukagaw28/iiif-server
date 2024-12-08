FROM python:3.11-alpine

ENV PYTHONUNBUFFERED 1

COPY Pipfile /
COPY Pipfile.lock /
RUN pip install pipenv
RUN pipenv install --system --deploy

COPY server.py /
COPY docker-entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

COPY ./api/ /api/
