import yaml
import logging
import logging.config
import connexion
from connexion import NoContent
import requests
from datetime import datetime
import uuid
from pykafka import KafkaClient
import json


with open('app_conf.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())

with open('log_conf.yml', 'r') as f:
    log_config = yaml.safe_load(f.read())
logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')


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

        # Produce Kafka message
        try:
            client = KafkaClient(hosts=f"{app_config['events']['hostname']}:{app_config['events']['port']}")
            topic = client.topics[app_config['events']['topic'].encode()]
            producer = topic.get_sync_producer()
        except Exception as kafka_init_error:
            logger.error(f"Failed to initialize Kafka: {str(kafka_init_error)}")
            return {"error": "Kafka initialization failed"}, 500

        msg = {
            "type": "sensor_data",
            "datetime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "payload": body
        }
        msg_str = json.dumps(msg)

        try:
            producer.produce(msg_str.encode('utf-8'))
        except Exception as produce_error:
            logger.error(f"Failed to produce message to Kafka: {str(produce_error)}")
            return {"error": "Failed to produce event"}, 500

        logger.info(f"Produced sensor data event with trace id: {trace_id}")

        # Forward the event to the storage service
        try:
            response = requests.post(app_config['eventstore1']['url'], json=body)
            if response.status_code != 201:
                logger.error(f"Failed to store sensor data in storage service: {response.text}")
                return {"error": "Failed to store event in storage service"}, 500
        except Exception as e:
            logger.error(f"Error forwarding to storage service: {str(e)}")
            return {"error": "Failed to forward event to storage service"}, 500

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

        # Kafka message
        try:
            client = KafkaClient(hosts=f"{app_config['events']['hostname']}:{app_config['events']['port']}")
            topic = client.topics[app_config['events']['topic'].encode()]
            producer = topic.get_sync_producer()
        except Exception as kafka_init_error:
            logger.error(f"Failed to initialize Kafka: {str(kafka_init_error)}")
            return {"error": "Kafka initialization failed"}, 500

        msg = {
            "type": "user_command",
            "datetime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "payload": body
        }
        msg_str = json.dumps(msg)

        try:
            producer.produce(msg_str.encode('utf-8'))
        except Exception as produce_error:
            logger.error(f"Failed to produce message to Kafka: {str(produce_error)}")
            return {"error": "Failed to produce event"}, 500

        logger.info(f"Produced user command event with trace id: {trace_id}")

        try:
            response = requests.post(app_config['eventstore2']['url'], json=body)
            if response.status_code != 201:
                logger.error(f"Failed to store user command in storage service: {response.text}")
                return {"error": "Failed to store event in storage service"}, 500
        except Exception as e:
            logger.error(f"Error forwarding to storage service: {str(e)}")
            return {"error": "Failed to forward event to storage service"}, 500

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


app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yml", strict_validation=False, validate_responses=True)

if __name__ == "__main__":
    logger.info("Starting the app...")
    app.run(host='0.0.0.0', port=8080)
