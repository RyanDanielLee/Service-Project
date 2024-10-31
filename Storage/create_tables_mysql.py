import mysql.connector

db_conn = mysql.connector.connect(host="", user="", 
                                  password="", database="")

db_cursor = db_conn.cursor()

# Create sensor_data table
db_cursor.execute('''
CREATE TABLE sensor_data
(id INT NOT NULL AUTO_INCREMENT,
sensor_id VARCHAR(250) NOT NULL,
temperature FLOAT NOT NULL,
timestamp VARCHAR(100) NOT NULL,
location VARCHAR(250) NOT NULL,
trace_id VARCHAR(100) NOT NULL,
date_created VARCHAR(100) NOT NULL,
CONSTRAINT sensor_data_pk PRIMARY KEY (id))
''')

# Create user_command table
db_cursor.execute('''
CREATE TABLE user_command
(id INT NOT NULL AUTO_INCREMENT,
user_id VARCHAR(250) NOT NULL,
target_device VARCHAR(250) NOT NULL,
target_temperature FLOAT NOT NULL,
timestamp VARCHAR(100) NOT NULL,
trace_id VARCHAR(100) NOT NULL,
date_created VARCHAR(100) NOT NULL,
CONSTRAINT user_command_pk PRIMARY KEY (id))
''')

db_conn.commit()
db_conn.close()
