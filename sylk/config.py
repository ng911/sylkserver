import os
import sys
from six import u

PSQL_DB_USER = "ng911ws"
PSQL_DB_PASS = "665pine94108"
PSQL_DB_IP = "161.35.229.154"
PSQL_DB_PORT = 5432
PSQL_DB_NAME = "ng911_test"
PSQL_IS_TEST_ENV = True

MONGODB_HOST = "rdffg.emergent911.com:27017"
MONGODB_DB = "ng911"
MONGODB_USERNAME = "ws"
MONGODB_PASSWORD = "emergent94108"
MONGODB_REPLICASET = ""
#MONGODB_URI = 'mongodb://localhost:27017/ng911'
#MONGODB_REPLICASET = "emergent911rs"
CREATE_DB = True

UPLOAD_FOLDER = "/resources"

FLASK_SERVER_PORT = 7070
USE_ASYNCIO=False

WAMP_REALM = u("realm1")
WAMP_CROSSBAR_SERVER = u("ws://rdffg-wamp.emergent911.com/ws")
#WAMP_CROSSBAR_SERVER = u"ws://crossbar-router:8080/ws"

MONGODB_URI = 'mongodb://%s:%s@%s/%s' % \
              (MONGODB_USERNAME, MONGODB_PASSWORD, MONGODB_HOST, MONGODB_DB)

#WAMP_CROSSBAR_SERVER = u"ws://crossbar-router:8080/ws"
WAMP_CONNECTION = WAMP_CROSSBAR_SERVER
SOP_DIR = "sop"

ALIDUMP_PORT = 12010
ALIDUMP_CLIENT_HOST = ""
ALIDUMP_CLIENT_PORT = ""
PSAP_BASE_DOMAIN = "test.emergentpsap.com"
USE_KAMAILIO = False
USE_AWS_ROUTE_53 = False
AWS_ACCESS_KEY=""
AWS_SECRET_KEY=""

def updateConfigFromEnv():
    tmp = globals().copy()
    gdefs = [k for k, v in tmp.items() if
           not k.startswith('_') and k != 'tmp' and k != 'In' and k != 'Out' and not hasattr(v, '__call__') and k != 'os']
    for gdef in gdefs:
        if gdef in os.environ:
            globals()[gdef] = os.environ[gdef]
            print("updated %s to %s" % (gdef, globals()[gdef]))
        #print("%s = %s" % (gdef, globals()[gdef]))


#if __name__ == '__main__':
updateConfigFromEnv()


