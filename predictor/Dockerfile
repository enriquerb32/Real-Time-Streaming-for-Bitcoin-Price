FROM python:3.8-slim

COPY requirements.txt .

RUN set -ex; \
  	pip install --no-cache-dir -r requirements.txt

# Copy resources
WORKDIR /
COPY wait.sh wait.sh

ADD predictor.py .

CMD ./wait.sh -s -t 30 $ZOOKEEPER_SERVER -- ./wait.sh -s -t 30 $KAFKA_SERVER -- ./wait.sh -s -t 30 $POSTGRES_SERVER -- python -u predictor.py