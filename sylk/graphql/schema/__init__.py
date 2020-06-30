import graphene
from graphene.relay import Node

from ..fields import OrderedMongoengineConnectionField, MongoengineObjectType
from .user import UserNode
from .psap import PsapNode
from .queue import QueueNode
from .speed_dial import SpeedDialNode, SpeedDialGroupNode
from .calls import ConferenceNode, resolveCalls, resolveActiveCall


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

graphql_schema = graphene.Schema(query=Query, types=[])

__all__ = [ 'graphql_schema']

