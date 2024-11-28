FROM python:3

LABEL maintainer="rlee356@my.bcit.ca"

RUN apt-get update -y && \
    apt-get install -y python3 python3-pip python3-venv curl

WORKDIR /app

RUN curl -sSLo /app/wait-for-it.sh https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh
RUN chmod +x /app/wait-for-it.sh

RUN python3 -m venv venv

RUN ./venv/bin/pip install --upgrade pip

COPY ./requirements.txt /app/requirements.txt
RUN ./venv/bin/pip install -r requirements.txt

COPY . /app

CMD [ "/bin/bash", "-c", "/app/wait-for-it.sh db:3306 -- ./venv/bin/python app.py" ]