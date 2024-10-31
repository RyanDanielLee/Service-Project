import mysql.connector

db_conn = mysql.connector.connect(host="", user="", 
                                  password="", database="")

db_cursor = db_conn.cursor()

# Drop the tables
db_cursor.execute('''
DROP TABLE IF EXISTS sensor_data, user_command
''')

db_conn.commit()
db_conn.close()
