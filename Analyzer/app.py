import connexion
import logging.config
import yaml
import json
from pykafka import KafkaClient
from pykafka.common import OffsetType
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware

with open('app_conf.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())

with open('log_conf.yml', 'r') as f:
    log_config = yaml.safe_load(f.read())
logging.config.dictConfig(log_config)
logger = logging.getLogger('basicLogger')

def get_sensor_data_reading(index):
    return get_event_from_kafka('sensor_data', index)

def get_user_command_reading(index):
    return get_event_from_kafka('user_command', index)

def get_event_from_kafka(event_type, index):
    hostname = f"{app_config['events']['hostname']}:{app_config['events']['port']}"
    client = KafkaClient(hosts=hostname)
    topic = client.topics[str.encode(app_config['events']['topic'])]
    consumer = topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=1000)

    try:
        for idx, msg in enumerate(consumer):
            if idx == index:
                msg_str = msg.value.decode('utf-8')
                msg = json.loads(msg_str)
                if msg['type'] == event_type:
                    logger.info(f"Returning {event_type} at index {index}")
                    return msg['payload'], 200
        return { "message": "Not Found" }, 404
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return { "message": "Error retrieving message" }, 500

def get_event_stats():
    hostname = f"{app_config['events']['hostname']}:{app_config['events']['port']}"
    client = KafkaClient(hosts=hostname)
    topic = client.topics[str.encode(app_config['events']['topic'])]
    consumer = topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=1000)

    num_sensor_data = 0
    num_user_command = 0

    try:
        for msg in consumer:
            msg_str = msg.value.decode('utf-8')
            msg = json.loads(msg_str)
            if msg['type'] == 'sensor_data':
                num_sensor_data += 1
            elif msg['type'] == 'user_command':
                num_user_command += 1

        stats = {
            "num_sensor_data": num_sensor_data,
            "num_user_command": num_user_command
        }
        return stats, 200
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return { "message": "Error retrieving statistics" }, 500

app = connexion.FlaskApp(__name__, specification_dir='./')
app.add_middleware(
    CORSMiddleware,
    position=MiddlewarePosition.BEFORE_EXCEPTION,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_api("openapi.yml")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8110)
