from graphene.relay import Node
from graphene_mongo import MongoengineObjectType

from ...db.schema import ChatMessage as MessageModel


class MessageNode(MongoengineObjectType):
    class Meta:
        model = MessageModel
        interfaces = (Node,)


