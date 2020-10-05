from aiohttp import web
from aiohttp_graphql import GraphQLView
import logging
from graphql_ws.aiohttp import AiohttpSubscriptionServer
import aiohttp_cors
import asyncio
from graphql.execution.executors.asyncio import AsyncioExecutor

from ..config import FLASK_SERVER_PORT
from .schema import graphene_schema

# aiohttp code taken from
# https://medium.com/@chimamireme/setting-up-a-modern-python-web-application-with-aiohttp-graphql-and-docker-149c52657142

log = logging.getLogger('emergent-ng911')

gqil_view = GraphQLView(
    schema=graphene_schema,
    executor=AsyncioExecutor(loop=asyncio.get_event_loop()),
    graphiql=True,
    enable_async=True,
    allow_subscriptions=True
)

gql_view = GraphQLView(
    schema=graphene_schema,
    executor=AsyncioExecutor(loop=asyncio.get_event_loop()),
    graphiql=False,
    enable_async=True,
    allow_subscriptions=True
)

subscription_server = AiohttpSubscriptionServer(graphene_schema)

async def subscriptions(request):
    log.info("inside subscriptions(request)")
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
    port = int(FLASK_SERVER_PORT)
    log.info("api server listening on port %d", port)
    web.run_app(app, host="0.0.0.0", port=port)




