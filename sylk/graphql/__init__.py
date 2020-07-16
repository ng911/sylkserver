from aiohttp import web
from flask import Flask, send_from_directory
from flask_session import Session
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from pymongo import MongoClient
from aiohttp_graphql import GraphQLView
import logging
from graphql_ws.aiohttp import AiohttpSubscriptionServer
import aiohttp_cors
import asyncio
from graphql.execution.executors.asyncio import AsyncioExecutor


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

gqil_view = GraphQLView(
    schema=graphql_schema,
    executor=AsyncioExecutor(loop=asyncio.get_event_loop()),
    graphiql=True,
    enable_async=True,
)

gql_view = GraphQLView(
    schema=graphql_schema,
    executor=AsyncioExecutor(loop=asyncio.get_event_loop()),
    graphiql=False,
    enable_async=True,
)

subscription_server = AiohttpSubscriptionServer(graphql_schema)

async def subscriptions(request):
    log.inof("inside subscriptions(request)")
    ws = web.WebSocketResponse(protocols=('graphql-ws',))
    await ws.prepare(request)

    await subscription_server.handle(ws)
    return ws



def init_routes(app, cors):
    app.router.add_route('*', '/graphiql', gqil_view, name='graphiql')

    resource = cors.add(app.router.add_resource("/graphql"), {
        "*": aiohttp_cors.ResourceOptions(
            expose_headers="*",
            allow_headers="*",
            allow_credentials=True,
            allow_methods=["POST", "PUT", "GET"]),
    })
    resource.add_route("POST", gql_view)
    resource.add_route("PUT", gql_view)
    resource.add_route("GET", gql_view)

    resource = cors.add(app.router.add_resource("/subscriptions"), {
        "*": aiohttp_cors.ResourceOptions(
            expose_headers="*",
            allow_headers="*",
            allow_credentials=True,
            allow_methods=["POST", "PUT", "GET"]),
    })

    resource.add_route("GET", subscriptions)
    resource.add_route("PUT", subscriptions)
    resource.add_route("POST", subscriptions)


app = web.Application()
cors = aiohttp_cors.setup(app)
init_routes(app, cors)


# Optional, for adding batch query support (used in Apollo-Client)
#GraphQLView.attach(app, schema=graphql_schema, route_path='/graphql', graphiql=True, subscriptions='/subscriptions')

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




