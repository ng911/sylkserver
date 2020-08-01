from graphene.relay import Node
from graphene_mongo import MongoengineObjectType
from graphene import ObjectType

from ..fields import EnhancedConnection
from ..fields import OrderedMongoengineConnectionField
from ...db.schema import ConferenceMessage as ConferenceMessageModel

from ..utiils import update_params_with_args


class MessageNode(MongoengineObjectType):
    class Meta:
        model = ConferenceMessageModel
        interfaces = (Node,)
        connection_class = EnhancedConnection


class PsapMessageNode(ObjectType):
    class Meta:
        interfaces = (Node,)
    messages = OrderedMongoengineConnectionField(MessageNode)

    @classmethod
    def get_node(cls, info, id):
        return f"PsapMessageNode{id}"

    def resolve_messages(parent, info, **args):
        params = {}
        update_params_with_args(params, args)
        return ConferenceMessageModel.objects(**params)
