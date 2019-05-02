FROM python:3.7-alpine

COPY ./docker-scripts/build-deps /install/build-deps
RUN /install/build-deps
COPY ./requirements.txt /install/requirements.txt

RUN pip3 install --upgrade pip
RUN pip3 install --no-cache-dir -r /install/requirements.txt

RUN apk add --no-cache bash

COPY ./docker.cfg /config/docker.cfg
ENV SPARROW_CONFIG=/config/docker.cfg

COPY ./docker-scripts/run /bin
EXPOSE 5000
RUN mkdir /app
WORKDIR /app

## Copy app core
COPY ./setup.py /app
COPY ./sparrow /app
RUN pip3 install -e .
CMD ["/bin/run"]