import asyncio
import graphene
from graphene.relay import Node
from graphene_sqlalchemy import SQLAlchemyConnectionField
from .psap import Psap
from .user import User

try:
    from sylk.applications import ApplicationLogger
    log = ApplicationLogger(__package__)
except:
    import logging
    log = logging.getLogger('emergent-ng911')


class Query(graphene.ObjectType):
    node = Node.Field()
    all_psaps = SQLAlchemyConnectionField(Psap.connection)
    all_users = SQLAlchemyConnectionField(User.connection)
    test_psaps = SQLAlchemyConnectionField(Psap.connection)
    def resolve_test_psaps(root, info, **args):
        query = Psap.get_query(info)  # SQLAlchemy query
        return query.all()


class Subscriptions(graphene.ObjectType):
    all_psaps = SQLAlchemyConnectionField(Psap.connection)
    async def resolve_all_psaps(root, info, **args):
        up_to = 10
        for i in range(up_to):
            query = Psap.get_query(info)  # SQLAlchemy query
            yield query.all()
            await asyncio.sleep(10.)

    psaps_la = SQLAlchemyConnectionField(Psap.connection)
    def resolve_all_psaps(root, info, **args):
        log.info("inside resolve_all_psaps subsriptions")
        up_to = 10
        for i in range(up_to):
            log.info("inside resolve_all_psaps subsriptions 1")
            query = Psap.get_query(info)  # SQLAlchemy query
            log.info("inside resolve_all_psaps subsriptions 2")
            return query.all()
            #log.info("inside resolve_all_psaps subsriptions 3")
            #await asyncio.sleep(10.)

graphene_schema = graphene.Schema(query=Query, subscription=Subscriptions, types=[])

__all__ = [ 'graphene_schema']

