from graphene.relay import Node
from graphene_mongo import MongoengineObjectType

from ..fields import EnhancedConnection
from ...db.schema import ConferenceMessage as ConferenceMessageModel


class MessageNode(MongoengineObjectType):
    class Meta:
        model = ConferenceMessageModel
        interfaces = (Node,)
        connection_class = EnhancedConnection

