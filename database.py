import pymysql
from flask import g

db_config = {
    'host': '',
    'user': '',
    'password': '',
    'db': '',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_database_connection():
    if 'db_conn' not in g:
        g.db_conn = pymysql.connect(**db_config)
    return g.db_conn

def create_connection():
    config = {k: v for k, v in db_config.items() if k != 'cursorclass'}
    return pymysql.connect(**config)

def close_conn(exception):
    db_conn = g.pop('db_conn', None)
    if db_conn:
        try:
            db_conn.close()
        except pymysql.MySQLError as e:
            print(f"Eroare la inchiderea conexiunii mysql: {str(e)}")