FROM python:3

LABEL maintainer="rlee356@my.bcit.ca"

RUN apt-get update -y && \
    apt-get install -y python3 python3-pip python3-venv

WORKDIR /app

RUN python3 -m venv venv

RUN ./venv/bin/pip install --upgrade pip

COPY ./requirements.txt /app/requirements.txt
RUN ./venv/bin/pip install -r requirements.txt

COPY . /app

ENTRYPOINT [ "./venv/bin/python" ]

CMD [ "app.py" ]