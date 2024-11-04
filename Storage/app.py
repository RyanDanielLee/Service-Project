'''
create_data.py in terminal

POST 
http://localhost:8090/sensor-data
{
    "sensorId": "123",
    "temperature": 22.5,
    "timestamp": "2024-09-19T10:00:00Z",
    "location": "Living Room"
}

POST
http://localhost:8090/user-command
{
  "userId": "user123",
  "targetDevice": "Thermostat",
  "targetTemperature": 21.0,
  "timestamp": "2024-09-19T10:05:00Z"
}

In terminal to check database
sqlite 
SELECT * FROM sensor_data;
SELECT * FROM user_command;
'''

import logging.config
import yaml
import connexion
from connexion import NoContent
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
from sensor_data import SensorData
from user_command import UserCommand
from base import Base
import uuid
import datetime
import json
from pykafka import KafkaClient
from pykafka.common import OffsetType
from threading import Thread



with open('app_conf.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())

with open('log_conf.yml', 'r') as f:
    log_config = yaml.safe_load(f.read())

logging.config.dictConfig(log_config)
logger = logging.getLogger('basicLogger')


logger.info(f"Connecting to MySQL database at {app_config['datastore']['hostname']}:{app_config['datastore']['port']}")

DB_ENGINE = create_engine(f"mysql+pymysql://{app_config['datastore']['user']}:{app_config['datastore']['password']}@{app_config['datastore']['hostname']}:{app_config['datastore']['port']}/{app_config['datastore']['db']}")
Base.metadata.bind = DB_ENGINE
DB_SESSION = sessionmaker(bind=DB_ENGINE)


def receive_sensor_data(body):
    session = DB_SESSION()
    
    trace_id = body.get('trace_id', str(uuid.uuid4()))

    sensor_data = SensorData(
        sensor_id=body['sensorId'], 
        temperature=body['temperature'], 
        timestamp=body['timestamp'], 
        location=body['location'],
        trace_id=trace_id,
        date_created=datetime.datetime.now()  
    )

    session.add(sensor_data)
    session.commit()
    session.close()

    logger.debug(f"Stored event 'sensor_data' request with a trace id of {trace_id}")

    return NoContent, 201


def receive_user_command(body):
    session = DB_SESSION()

    trace_id = body.get('trace_id', str(uuid.uuid4()))

    user_command = UserCommand(
        user_id=body['userId'], 
        target_device=body['targetDevice'], 
        target_temperature=body['targetTemperature'], 
        timestamp=body['timestamp'],
        trace_id=trace_id,
        date_created=datetime.datetime.now()  
    )

    session.add(user_command)
    session.commit()
    session.close()

    logger.debug(f"Stored event 'user_command' request with a trace id of {trace_id}")

    return NoContent, 201


def get_sensor_data_readings(start_timestamp, end_timestamp):
    try:
        session = DB_SESSION()

        start_timestamp = start_timestamp.strip()
        end_timestamp = end_timestamp.strip()

        try:
            start_timestamp_datetime = datetime.datetime.strptime(start_timestamp, "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            start_timestamp_datetime = datetime.datetime.strptime(start_timestamp, "%Y-%m-%dT%H:%M:%S")

        try:
            end_timestamp_datetime = datetime.datetime.strptime(end_timestamp, "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            end_timestamp_datetime = datetime.datetime.strptime(end_timestamp, "%Y-%m-%dT%H:%M:%S")

        readings = session.query(SensorData).filter(
            and_(SensorData.date_created >= start_timestamp_datetime,
                 SensorData.date_created < end_timestamp_datetime)
        )

        results_list = [reading.to_dict() for reading in readings]
        session.close()

        logger.info("Query for sensor data readings after %s returns %d results" % 
                    (start_timestamp, len(results_list)))

        return results_list, 200
    except Exception as e:
        logger.error(f"Error retrieving sensor data: {str(e)}")
        return {"message": str(e)}, 500



def get_user_command_events(start_timestamp, end_timestamp):
    session = DB_SESSION()
    
    start_timestamp_datetime = datetime.datetime.strptime(start_timestamp, "%Y-%m-%dT%H:%M:%S")
    end_timestamp_datetime = datetime.datetime.strptime(end_timestamp, "%Y-%m-%dT%H:%M:%S")
    
    commands = session.query(UserCommand).filter(
        and_(UserCommand.date_created >= start_timestamp_datetime,
             UserCommand.date_created < end_timestamp_datetime)
    )
    
    results_list = [command.to_dict() for command in commands]
    session.close()
    
    logger.info("Query for user command events after %s returns %d results" % 
                (start_timestamp, len(results_list)))
    
    return results_list, 200

def process_messages():
    hostname = f"{app_config['events']['hostname']}:{app_config['events']['port']}"
    client = KafkaClient(hosts=hostname)
    topic = client.topics[str.encode(app_config['events']['topic'])]
    consumer = topic.get_simple_consumer(consumer_group=b'event_group',
                                         reset_offset_on_start=False,
                                         auto_offset_reset=OffsetType.LATEST)
    for msg in consumer:
        msg_str = msg.value.decode('utf-8')
        msg = json.loads(msg_str)
        logger.info("Message: %s" % msg)
        payload = msg['payload']
        if msg['type'] == 'sensor-data':
            receive_sensor_data(payload)
        elif msg['type'] == 'user-command':
            receive_user_command(payload)
        consumer.commit_offsets()



app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    t1 = Thread(target=process_messages)
    t1.setDaemon(True)
    t1.start()
    app.run(host='0.0.0.0', port=8090)

