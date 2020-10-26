import graphene
import logging
from graphene.relay import Node
from graphene_mongo import MongoengineConnectionField, MongoengineObjectType

from ..fields import EnhancedConnection
from ..types import EnhancedMongoengineObjectType
from ..utiils import update_params_with_args
from ..mutations import get_id_from_node_id
from ...db.schema import CallTransferLine as CallTransferLineModel


class CallTransferLineNode(MongoengineObjectType):
    class Meta:
        model = CallTransferLineModel
        interfaces = (Node,)
        connection_class = EnhancedConnection


from ..mutations import create_update_mutation, create_insert_mutation, create_delete_mutation, EnhancedClientIDMutation

class CreateCallTransferLineMutation(EnhancedClientIDMutation):
    @classmethod
    def __custom__(cls):
        create_insert_mutation(cls, CallTransferLineModel, CallTransferLineNode)


class UpdateCallTransferLineMutation(EnhancedClientIDMutation):
    @classmethod
    def __custom__(cls):
        create_update_mutation(cls, CallTransferLineModel, CallTransferLineNode, 'line_id')


class DeleteCallTransferLineMutation(EnhancedClientIDMutation):
    @classmethod
    def __custom__(cls):
        create_delete_mutation(cls, CallTransferLineModel)


