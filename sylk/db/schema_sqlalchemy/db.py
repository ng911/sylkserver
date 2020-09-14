from sqlalchemy import create_engine
from ...config import PSQL_DB_USER, PSQL_DB_IP, PSQL_DB_PASS, PSQL_DB_NAME, PSQL_DB_PORT
from uuid import uuid4

def connect_db():
    #_load_db_vars()
    # create db create_engine
    db = create_engine(f'postgresql://{PSQL_DB_USER}:{PSQL_DB_PASS}@{PSQL_DB_IP}:{PSQL_DB_PORT}/{PSQL_DB_NAME}')
    return db


def getUniqueId():
    return str(uuid4())

engine = connect_db()

