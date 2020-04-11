import graphene
from graphene.relay import Node

from ..fields import OrderedMongoengineConnectionField
from .user import UserNode
from .psap import PsapNode
from .queue import QueueNode
from .speed_dial import SpeedDialNode
from .calls import ConferenceNode


class Query(graphene.ObjectType):
    node = Node.Field()

    name = graphene.String()
    all_users = OrderedMongoengineConnectionField(UserNode)
    all_psaps = OrderedMongoengineConnectionField(PsapNode)
    all_queues = OrderedMongoengineConnectionField(QueueNode)
    all_speed_dials = OrderedMongoengineConnectionField(SpeedDialNode)
    all_conferences = OrderedMongoengineConnectionField(ConferenceNode)

    def resolve_name(parent, info, **args):
        return "Hello World"


graphql_schema = graphene.Schema(query=Query, types=[])

__all__ = [ 'graphql_schema']

