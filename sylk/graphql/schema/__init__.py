import graphene
from graphene.relay import Node

from ..fields import OrderedMongoengineConnectionField
from .user import UserNode
from .psap import PsapNode
from .queue import QueueNode
from .speed_dial import SpeedDialNode, SpeedDialGroupNode
from .calls import ConferenceNode, resolveCalls


class Query(graphene.ObjectType):
    node = Node.Field()
    all_users = OrderedMongoengineConnectionField(UserNode)
    '''
    all_psaps = OrderedMongoengineConnectionField(PsapNode)
    all_queues = OrderedMongoengineConnectionField(QueueNode)
    all_speed_dials = OrderedMongoengineConnectionField(SpeedDialNode)
    all_speed_dial_groups = OrderedMongoengineConnectionField(SpeedDialGroupNode)
    all_conferences = OrderedMongoengineConnectionField(ConferenceNode, \
                                                        psap_id=graphene.String(required=True), \
                                                        calling_number=graphene.String(required=False), \
                                                        start_time=graphene.String(required=False), \
                                                        end_time=graphene.String(required=False), \
                                                        location=graphene.String(required=False),
                                                        note=graphene.String(required=False))

    def resolve_all_conferences(parent, info, **args):
        return resolveCalls(parent, info, **args)
    '''

graphql_schema = graphene.Schema(query=Query, types=[])

__all__ = [ 'graphql_schema']

