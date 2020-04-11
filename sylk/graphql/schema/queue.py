import graphene
from graphene import Field, List, String
from graphene.relay import Node
from graphene_mongo import MongoengineConnectionField, MongoengineObjectType

from ..utiils import update_params_with_args
from ...db.schema import Queue as QueueModel
from ...db.schema import QueueMember
from ...db.schema import User as UserModel


class UserDataNode(MongoengineObjectType):
    class Meta:
        model = UserModel
        interfaces = (Node,)


class QueueNode(MongoengineObjectType):
    class Meta:
        model = QueueModel
        interfaces = (Node,)

    members = MongoengineConnectionField(UserDataNode)

    def resolve_members(parent, info, **args):
        params = {
            "queue_id" : parent.queue_id
        }

        user_ids = []
        for queueMember in QueueMember.objects(**params):
            user_ids.append(queueMember.user_id)

        return UserModel.objects(user_id__in = user_ids)


