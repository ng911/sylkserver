import graphene
from graphene.relay import Node

from ..fields import OrderedMongoengineConnectionField, MongoengineObjectType
from .user import UserNode, UpdateUserMutation
from .psap import PsapNode, CreatePsapMutation, UpdatePsapMutation
from .queue import QueueNode
from .speed_dial import SpeedDialNode, SpeedDialGroupNode
from .calls import ConferenceNode, resolveCalls, resolveActiveCall

try:
    from sylk.applications import ApplicationLogger
    log = ApplicationLogger(__package__)
except:
    import logging
    log = logging.getLogger('emergent-ng911')


class Query(graphene.ObjectType):
    node = Node.Field()
    all_users = OrderedMongoengineConnectionField(UserNode)
    all_psaps = OrderedMongoengineConnectionField(PsapNode)
    all_queues = OrderedMongoengineConnectionField(QueueNode)
    all_speed_dials = OrderedMongoengineConnectionField(SpeedDialNode)
    all_speed_dial_groups = OrderedMongoengineConnectionField(SpeedDialGroupNode)
    all_conferences = OrderedMongoengineConnectionField(ConferenceNode, \
                                                        calling_number=graphene.String(required=False), \
                                                        location=graphene.String(required=False))
    # active call for a calltaker
    active_call = graphene.Field(ConferenceNode, username=graphene.String(required=True))

    def resolve_active_call(parent, info, **args):
        return resolveActiveCall(parent, info, **args)
    #def resolve_all_conferences(parent, info, **args):
    #    return resolveCalls(parent, info, **args)

class Subscriptions(graphene.ObjectType):
    count_seconds = graphene.Float(up_to=graphene.Int())

    async def resolve_count_seconds(root, info, up_to):
        log.info("inside resolve_count_seconds")
        for i in range(up_to):
            yield i
            await asyncio.sleep(1.)
        yield up_to


class Mutations(graphene.ObjectType):
    update_user = UpdateUserMutation.Field()
    create_psap = CreatePsapMutation.Field()
    update_psap = UpdatePsapMutation.Field()


graphql_schema = graphene.Schema(query=Query, mutation=Mutations, subscription=Subscriptions, types=[])

__all__ = [ 'graphql_schema']

