import graphene
from graphene import Field, List, String
from graphene.relay import Node
from graphene_mongo import MongoengineConnectionField, MongoengineObjectType

from ..fields import EnhancedConnection
from ..utiils import update_params_with_args
from ...db.schema import Queue as QueueModel
from ...db.schema import QueueMember as QueueMemberModel
from ...db.schema import User as UserModel


class UserDataNode(MongoengineObjectType):
    class Meta:
        model = UserModel
        interfaces = (Node,)


class QueueNode(MongoengineObjectType):
    class Meta:
        model = QueueModel
        interfaces = (Node,)
        connection_class = EnhancedConnection

    members = MongoengineConnectionField(UserDataNode)

    def resolve_members(parent, info, **args):
        params = {
            "queue_id" : parent.queue_id
        }

        user_ids = []
        for queueMember in QueueMemberModel.objects(**params):
            user_ids.append(queueMember.user_id)

        return UserModel.objects(user_id__in = user_ids)


class QueueMemberNode(MongoengineObjectType):
    class Meta:
        model = QueueMemberModel
        interfaces = (Node,)
        connection_class = EnhancedConnection


from ..mutations import create_insert_mutation, create_update_mutation, create_delete_mutation, \
    EnhancedClientIDMutation


class CreateQueueMutation(EnhancedClientIDMutation):
    @classmethod
    def __custom__(cls):
        create_insert_mutation(cls, QueueModel, QueueNode)


class UpdateQueueMutation(EnhancedClientIDMutation):
    @classmethod
    def __custom__(cls):
        create_update_mutation(cls, QueueModel, QueueNode, 'queue_id')


class DeleteCallTransferLineMutation(EnhancedClientIDMutation):
    @classmethod
    def __custom__(cls):
        create_delete_mutation(cls, QueueModel)

class CreateQueueMemberMutation(EnhancedClientIDMutation):
    @classmethod
    def __custom__(cls):
        create_insert_mutation(cls, QueueMemberModel, QueueMemberNode)


class UpdateQueueMemberMutation(EnhancedClientIDMutation):
    @classmethod
    def __custom__(cls):
        create_update_mutation(cls, QueueMemberModel, QueueMemberNode, 'id')


class DeleteMemberMutation(EnhancedClientIDMutation):
    @classmethod
    def __custom__(cls):
        create_delete_mutation(cls, QueueMemberModel)
