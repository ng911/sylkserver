import graphene
import logging
from graphene.relay import Node
from graphene_mongo import MongoengineConnectionField, MongoengineObjectType

from ..fields import EnhancedConnection
from ..utiils import update_params_with_args
from ...db.schema import User as UserModel
from ...db.schema import CalltakerProfile as CalltakerProfileModel
from ...db.schema import Queue as QueueModel
from ...db.schema import QueueMember as QueueMemberModel

log = logging.getLogger("emergent-ng911")


class UserProfileNode(MongoengineObjectType):
    class Meta:
        model = CalltakerProfileModel
        interfaces = (Node,)


class UserNode(MongoengineObjectType):
    class Meta:
        model = UserModel
        interfaces = (Node,)
        connection_class = EnhancedConnection

    from .queue import QueueNode
    queues = MongoengineConnectionField(QueueNode)
    profile = MongoengineObjectType()

    def resolve_queues(parent, info, **args):
        queue_ids = []
        for queue in QueueMemberModel.objects(user_id = parent.user_id):
            queue_ids.append(str(queue.queue_id))
        return QueueModel.objects(queue_id__in = queue_ids)

    def resolve_profile(parent, info, **args):
        params = {
            "user_id" : parent.user_id
        }
        return CalltakerProfileModel.objects.get(**params)

class PsapUsersNode(graphene.ObjectType):
    class Meta:
        interfaces = (Node,)
    users = MongoengineConnectionField(UserNode)

    @classmethod
    def get_node(cls, info, id):
        return f"PsapUsersNode{id}"

    def resolve_users(parent, info, **args):
        params = {}
        update_params_with_args(params, args)
        return UserModel.objects(**params)


from ..mutations import create_update_mutation, create_insert_mutation, EnhancedClientIDMutation

class CreateUserMutation(EnhancedClientIDMutation):
    @classmethod
    def __custom__(cls):
        create_insert_mutation(cls, UserModel, UserNode)

class UpdateUserMutation(EnhancedClientIDMutation):
    @classmethod
    def __custom__(cls):
        create_update_mutation(cls, UserModel, UserNode, 'user_id')


