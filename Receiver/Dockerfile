FROM ubuntu:24.04

LABEL maintainer="rlee356@my.bcit.ca" 

RUN apt-get update -y && \
    apt-get install -y python3 python3-pip

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt
RUN pip3 install -r requirements.txt

COPY . /app

EXPOSE 8080

ENTRYPOINT [ "python3" ]

CMD [ "app.py" ]
