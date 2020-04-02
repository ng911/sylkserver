import os

WAMP_CONNECTION = "wss://staging-webservice.supportgenie.io/ws"
WAMP_REALM = "realm1"

MONGODB_HOST = "mongodb:27017"
MONGODB_DB = "ng911"
MONGODB_USERNAME = "ws"
MONGODB_PASSWORD = "emergent94108"
CREATE_DB = True

FLASK_SERVER_PORT = 7070


def updateConfigFromEnv():
    tmp = globals().copy()
    gdefs = [k for k, v in tmp.items() if
           not k.startswith('_') and k != 'tmp' and k != 'In' and k != 'Out' and not hasattr(v, '__call__') and k != 'os']
    for gdef in gdefs:
        if gdef in os.environ:
            globals()[gdef] = os.environ[gdef]
            print("updated %s to %s" % (gdef, globals()[gdef]))
        #print("%s = %s" % (gdef, globals()[gdef]))


if __name__ == '__main__':
    updateConfigFromEnv()


