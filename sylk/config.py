import os
import sys


MONGODB_HOST = "mongodb:27017"
MONGODB_DB = "ng911"
MONGODB_USERNAME = "ws"
MONGODB_PASSWORD = "emergent94108"
MONGODB_REPLICASET = ""
MONGODB_URI = 'mongodb://%s:%s@%s/%s' % \
              (MONGODB_USERNAME, MONGODB_PASSWORD, MONGODB_HOST, MONGODB_DB)
#MONGODB_URI = 'mongodb://localhost:27017/ng911'

#MONGODB_REPLICASET = "emergent911rs"
CREATE_DB = True

FLASK_SERVER_PORT = 7070


if (sys.version_info > (3, 0)):
    WAMP_REALM = "realm1"
    WAMP_CROSSBAR_SERVER = "wss://webservice.emergent911.com/ws"
else:
    WAMP_REALM = u"realm1"
    WAMP_CROSSBAR_SERVER = u"wss://webservice.emergent911.com/ws"
#WAMP_CROSSBAR_SERVER = u"ws://crossbar-router:8080/ws"
WAMP_CONNECTION = WAMP_CROSSBAR_SERVER
SOP_DIR = "sop"

ALIDUMP_PORT = 12010
ALIDUMP_CLIENT_HOST = ""
ALIDUMP_CLIENT_PORT = ""


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


