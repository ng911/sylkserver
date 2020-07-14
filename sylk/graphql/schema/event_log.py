from graphene.relay import Node
from graphene_mongo import MongoengineObjectType

from ..fields import EnhancedConnection
from ...db.schema import ConferenceEvent as ConferenceEventModel


class EventLogNode(MongoengineObjectType):
    class Meta:
        model = ConferenceEventModel
        interfaces = (Node,)
        connection_class = EnhancedConnection

