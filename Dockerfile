FROM python:3
ENV PYTHONUNBUFFERED 1
ADD Pipfile /Pipfile
ADD Pipfile.lock /Pipfile.lock
RUN pip install pipenv
RUN pipenv install --system --deploy
WORKDIR /code
ADD docker-entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
