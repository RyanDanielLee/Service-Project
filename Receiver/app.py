import os
import yaml
import logging
import logging.config
import connexion
from connexion import NoContent
import requests
from datetime import datetime
import uuid
import time
from pykafka import KafkaClient
from pykafka.exceptions import KafkaException
import json

if "TARGET_ENV" in os.environ and os.environ["TARGET_ENV"] == "test":
    print("In Test Environment")
    app_conf_file = "/config/app_conf.yml"
    log_conf_file = "/config/log_conf.yml"
else:
    print("In Dev Environment")
    app_conf_file = "app_conf.yml"
    log_conf_file = "log_conf.yml"

# Load configurations
with open('app_conf.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())

with open('log_conf.yml', 'r') as f:
    log_config = yaml.safe_load(f.read())

logging.config.dictConfig(log_config)
logger = logging.getLogger('basicLogger')
logger.info("App Conf File: %s" % app_conf_file)
logger.info("Log Conf File: %s" % log_conf_file)

# Constants for retry logic
MAX_RETRIES = 5
RETRY_INTERVAL = 10  # seconds


def initialize_kafka_client():
    """Initialize Kafka client with retry logic."""
    retries = 0
    while retries < MAX_RETRIES:
        try:
            logger.info(f"Attempting to connect to Kafka (attempt {retries + 1}/{MAX_RETRIES})...")
            kafka_client = KafkaClient(hosts=f"{app_config['events']['hostname']}:{app_config['events']['port']}")
            kafka_topic = kafka_client.topics[app_config['events']['topic'].encode()]
            kafka_producer = kafka_topic.get_sync_producer()
            logger.info("Kafka client connected successfully.")
            return kafka_producer
        except KafkaException as e:
            logger.warning(f"Failed to connect to Kafka: {str(e)}")
            retries += 1
            if retries < MAX_RETRIES:
                logger.info(f"Retrying in {RETRY_INTERVAL} seconds...")
                time.sleep(RETRY_INTERVAL)
            else:
                logger.error("Max retries reached. Kafka connection failed.")
                return None


# Initialize Kafka producer on service startup
kafka_producer = initialize_kafka_client()


def receive_sensor_data(body):
    try:
        required_fields = ['temperature', 'timestamp', 'sensorId', 'location']
        for field in required_fields:
            if field not in body:
                logger.error(f"Missing key: {field}")
                return {"error": f"Missing key: {field}"}, 400

        trace_id = str(uuid.uuid4())
        event_name = "sensor_data"
        logger.info(f"Received event {event_name} request with a trace id of {trace_id}")

        body['trace_id'] = trace_id

        if kafka_producer is None:
            logger.error("Kafka producer is not initialized.")
            return {"error": "Kafka unavailable"}, 500

        msg = {
            "type": "sensor_data",
            "datetime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "payload": body
        }
        msg_str = json.dumps(msg)

        try:
            kafka_producer.produce(msg_str.encode('utf-8'))
            logger.info(f"Produced sensor data event with trace id: {trace_id}")
        except Exception as produce_error:
            logger.error(f"Failed to produce message to Kafka: {str(produce_error)}")
            return {"error": "Failed to produce event"}, 500

        return NoContent, 201

    except Exception as e:
        logger.error(f"Unexpected error in receive_sensor_data: {str(e)}")
        return {"error": "Internal server error"}, 500


def receive_user_command(body):
    try:
        required_fields = ['timestamp', 'userId', 'targetDevice', 'targetTemperature']
        for field in required_fields:
            if field not in body:
                logger.error(f"Missing key: {field}")
                return {"error": f"Missing key: {field}"}, 400

        trace_id = str(uuid.uuid4())
        event_name = "user_command"
        logger.info(f"Received event {event_name} request with a trace id of {trace_id}")

        body['trace_id'] = trace_id

        if kafka_producer is None:
            logger.error("Kafka producer is not initialized.")
            return {"error": "Kafka unavailable"}, 500

        msg = {
            "type": "user_command",
            "datetime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "payload": body
        }
        msg_str = json.dumps(msg)

        try:
            kafka_producer.produce(msg_str.encode('utf-8'))
            logger.info(f"Produced user command event with trace id: {trace_id}")
        except Exception as produce_error:
            logger.error(f"Failed to produce message to Kafka: {str(produce_error)}")
            return {"error": "Failed to produce event"}, 500

        return NoContent, 201

    except Exception as e:
        logger.error(f"Unexpected error in receive_user_command: {str(e)}")
        return {"error": "Internal server error"}, 500


def get_sensor_data_readings():
    data = requests.args
    response = requests.get(app_config['eventstore1']['url'], params=data)
    return NoContent, response.status_code


def get_user_command_events():
    data = requests.args
    response = requests.get(app_config['eventstore2']['url'], params=data)
    return NoContent, response.status_code


# Start the application
app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yml", strict_validation=False, validate_responses=True)

if __name__ == "__main__":
    logger.info("Starting the app...")
    app.run(host='0.0.0.0', port=8080)