from flask import Flask, send_from_directory
from flask_session import Session
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from pymongo import MongoClient
from twisted.internet import reactor
from twisted.web.server import Site
from twisted.web.wsgi import WSGIResource
from flask_graphql import GraphQLView
import logging

from ..config import MONGODB_HOST, MONGODB_DB, MONGODB_USERNAME, MONGODB_PASSWORD
from ..config import FLASK_SERVER_PORT
from .schema import graphql_schema


logger = logging.getLogger('kingfisher')


def create_app():
    app = Flask(__name__)

    # from https://stackoverflow.com/questions/23347387/x-forwarded-proto-and-flask
    app.wsgi_app = ProxyFix(app.wsgi_app)
    app.secret_key = 'best ng911 system, supercharged with webrtc'
    app.config['SESSION_TYPE'] = 'mongodb'

    mongo_uri = 'mongodb://{}/{}'.format(MONGODB_HOST, MONGODB_DB)
    mongo_client = MongoClient(mongo_uri, username=MONGODB_USERNAME, password=MONGODB_PASSWORD)
    app.config['SESSION_MONGODB'] = mongo_client
    app.config['SESSION_MONGODB_DB'] = MONGODB_DB
    app.config['SESSION_MONGODB_COLLECT'] = 'web_sessions'
    return app

app = create_app()
Session(app)

CORS(app)

app.add_url_rule('/graphql', view_func=GraphQLView.as_view('graphql', schema=graphql_schema, graphiql=True))

@app.route('/')
def index():
    return 'My Twisted Flask root'

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)


def start_server():
    logger.info("start graphql api server")
    flask_resource = WSGIResource(reactor, reactor.getThreadPool(), app)
    flask_site = Site(flask_resource)
    logger.info("api server listening on port %d", int(FLASK_SERVER_PORT))
    reactor.listenTCP(int(FLASK_SERVER_PORT), flask_site, interface="0.0.0.0")




