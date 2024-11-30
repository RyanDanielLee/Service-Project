import os
import logging
import logging.config
import connexion
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import json
from datetime import datetime
import yaml
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware

if "TARGET_ENV" in os.environ and os.environ["TARGET_ENV"] == "test":
    print("In Test Environment")
    app_conf_file = "/config/app_conf.yml"
    log_conf_file = "/config/log_conf.yml"
else:
    print("In Dev Environment")
    app_conf_file = "app_conf.yml"
    log_conf_file = "log_conf.yml"

with open('app_conf.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())

with open('log_conf.yml', 'r') as f:
    log_config = yaml.safe_load(f.read())

logging.config.dictConfig(log_config)
logger = logging.getLogger('basicLogger')
logger.info("App Conf File: %s" % app_conf_file)
logger.info("Log Conf File: %s" % log_conf_file)

stats_file = app_config['datastore']['filename']

# Ensure the stats file exists with an empty stats table
def initialize_stats_file():
    if not os.path.exists(stats_file):
        logger.info(f"{stats_file} does not exist. Initializing with default values.")
        initial_stats = {
            "num_sensor_data_events": 0,
            "max_temperature": 0,
            "num_user_commands": 0,
            "max_target_temperature": 0,
            "last_updated": datetime.now().isoformat()
        }
        with open(stats_file, 'w') as file:
            json.dump(initial_stats, file)
    else:
        logger.info(f"{stats_file} already exists.")

initialize_stats_file()

def format_timestamp(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%S')

def populate_stats():
    logger.info("Starting periodic processing")

    try:
        with open(stats_file, 'r') as file:
            stats = json.load(file)
    except FileNotFoundError:
        logger.error("Statistics file not found during periodic processing.")
        return

    last_updated = datetime.fromisoformat(stats["last_updated"])
    formatted_last_updated = last_updated.strftime("%Y-%m-%dT%H:%M:%S")
    current_time = format_timestamp(datetime.now())
    logger.debug(f"Fetching new data between {formatted_last_updated} and {current_time}")

    # Query sensor data events
    sensor_data_url = f"{app_config['eventstore']['url']}/sensor-data"
    try:
        sensor_data = requests.get(sensor_data_url, params={"start_timestamp": formatted_last_updated, "end_timestamp": current_time})
        logger.debug(f"Sensor data response status code: {sensor_data.status_code}")

        if sensor_data.status_code != 200:
            logger.error(f"Error fetching sensor data, status code: {sensor_data.status_code}")
            return

        sensor_data_events = sensor_data.json()
        logger.info(f"Received {len(sensor_data_events)} sensor data events")

        # Process sensor data events
        for event in sensor_data_events:
            stats['num_sensor_data_events'] += 1
            stats['max_temperature'] = max(stats['max_temperature'], event.get('temperature', 0))

    except Exception as e:
        logger.error(f"Error processing sensor data: {e}")

    # Query user command events
    try:
        user_commands = requests.get(f"{app_config['eventstore']['url']}/user-command?start_timestamp={formatted_last_updated}&end_timestamp={current_time}")
        logger.debug(f"User command response status code: {user_commands.status_code}")

        if user_commands.status_code != 200:
            logger.error(f"Error fetching user commands, status code: {user_commands.status_code}")
            return

        user_command_events = user_commands.json()
        logger.info(f"Received {len(user_command_events)} user command events")

        # Process user command events
        for event in user_command_events:
            stats['num_user_commands'] += 1
            stats['max_target_temperature'] = max(stats['max_target_temperature'], event.get('target_temperature', 0))

    except Exception as e:
        logger.error(f"Error processing user commands: {e}")

    stats['last_updated'] = current_time

    with open(stats_file, 'w') as file:
        json.dump(stats, file)

    logger.debug(f"Updated statistics: {stats}")
    logger.info("Periodic processing completed")


def get_stats():
    logger.info("Request received for event stats")
    try:
        # Load the current stats from the file
        with open(stats_file, 'r') as file:
            stats = json.load(file)
        return stats, 200
    except FileNotFoundError:
        logger.error("Statistics file not found")
        return {"message": "Statistics do not exist"}, 404

def init_scheduler():
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(populate_stats, 'interval', seconds=app_config['scheduler']['period_sec'])
    sched.start()

app = connexion.FlaskApp(__name__, specification_dir='')
app.add_middleware(
    CORSMiddleware,
    position=MiddlewarePosition.BEFORE_EXCEPTION,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_api("openapi.yml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    init_scheduler()
    app.run(host='0.0.0.0', port=8100)