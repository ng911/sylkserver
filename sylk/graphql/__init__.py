from aiohttp import web
from flask import Flask, send_from_directory
from flask_session import Session
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from pymongo import MongoClient
from aiohttp_graphql import GraphQLView
import logging
from graphql_ws.aiohttp import AiohttpSubscriptionServer

from ..config import MONGODB_HOST, MONGODB_DB, MONGODB_USERNAME, MONGODB_PASSWORD
from ..config import FLASK_SERVER_PORT
from .schema import graphql_schema


log = logging.getLogger('emergent-ng911')


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
'''
app = create_app()
Session(app)

CORS(app)

app.add_url_rule('/graphql', view_func=GraphQLView.as_view('graphql', schema=graphql_schema, graphiql=True))
'''
app = web.Application()

# Optional, for adding batch query support (used in Apollo-Client)
GraphQLView.attach(app, schema=graphql_schema, batch=True, enable_async=True, graphiql=True, subscriptions='/subscriptions')

subscription_server = AiohttpSubscriptionServer(schema)

async def subscriptions(request):
    ws = web.WebSocketResponse(protocols=('graphql-ws',))
    await ws.prepare(request)

    await subscription_server.handle(ws)
    return ws


app.router.add_get('/subscriptions', subscriptions)

def start_server():
    log.info("start graphql api server")
    '''
    flask_resource = WSGIResource(reactor, reactor.getThreadPool(), app)
    flask_site = Site(flask_resource)
    log.info("api server listening on port %d", int(FLASK_SERVER_PORT))
    reactor.listenTCP(int(FLASK_SERVER_PORT), flask_site, interface="0.0.0.0")
    '''
    port = int(FLASK_SERVER_PORT)
    log.info("api server listening on port %d", port)
    web.run_app(app, host="0.0.0.0", port=port)




