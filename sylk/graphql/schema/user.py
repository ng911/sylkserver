import graphene
import logging
from graphene.relay import Node
from graphene_mongo import MongoengineConnectionField, MongoengineObjectType

from ..fields import EnhancedConnection
from ..utiils import update_params_with_args
from ..mutations import get_id_from_node_id
from ...db.schema import User as UserModel
from ...db.schema import UserGroup as UserGroupModel
from ...db.schema import Role as RoleModel
from ...db.schema import Skillset as SkillsetModel
from ...db.schema import UserPermission as UserPermissionModel
from ...db.schema import CalltakerProfile as CalltakerProfileModel
from ...db.schema import Queue as QueueModel
from ...db.schema import QueueMember as QueueMemberModel

log = logging.getLogger("emergent-ng911")


class UserPermissionNode(MongoengineObjectType):
    class Meta:
        model = UserPermissionModel
        interfaces = (Node,)


class UserGroupNode(MongoengineObjectType):
    class Meta:
        model = UserGroupModel
        interfaces = (Node,)

    permissions = graphene.List(of_type=graphene.String)

    def resolve_permissions(parent, info, **args):
        permissions = []
        permission_ids = parent.permissions
        for permissionObj in UserPermissionModel.objects(id__in = permission_ids):
            permissions.append(permissionObj.name)
        return permissions


def resolveUserGroups(parent, info, **args):
    groups = []
    params = {
        "psap_id__exists" : False
    }
    for dbObj in UserGroupModel.objects(**params):
        group = dbObj.name
        if group not in groups:
            groups.append(group)
    params = {
        "psap_id" : args["psap_id"]
    }
    for dbObj in UserGroupModel.objects(**params):
        group = dbObj.name
        if group not in groups:
            groups.append(group)
    return groups


class RoleNode(MongoengineObjectType):
    class Meta:
        model = RoleModel
        interfaces = (Node,)


class SkillsetNode(MongoengineObjectType):
    class Meta:
        model = SkillsetModel
        interfaces = (Node,)


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
    group = MongoengineConnectionField(UserGroupNode)
    skillset_nodes = MongoengineConnectionField(SkillsetNode)
    role_nodes = MongoengineConnectionField(RoleNode)
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

    def resolve_skillset_nodes(parent, info, **args):
        return SkillsetModel.objects(id__in = parent.skillsets)

    def resolve_role__nodes(parent, info, **args):
        return RoleModel.objects(id__in = parent.roles)


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


class CreateRoleMutation(EnhancedClientIDMutation):
    @classmethod
    def __custom__(cls):
        create_insert_mutation(cls, RoleModel, RoleNode)


class UpdateRoleMutation(EnhancedClientIDMutation):
    @classmethod
    def __custom__(cls):
        create_update_mutation(cls, RoleModel, RoleNode)


class DeleteRoleMutation(EnhancedClientIDMutation):
    success = graphene.Field(graphene.Boolean)

    class Input:
        id = graphene.ID(required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        from ..mutations import get_id_from_node_id
        from bson import ObjectId
        node_id = input.get('id')
        id_ = get_id_from_node_id(node_id)
        roleObj = RoleModel.objects.get(pk=id_)
        psap_id = roleObj.psap_id
        for userObj in UserModel.objects(psap_id=psap_id):
            bson_id_ = ObjectId(id_)
            if  bson_id_ in userObj.roles:
                userObj.roles.remove(bson_id_)
                userObj.save()
        roleObj.delete()
        return DeleteRoleMutation(success=True)


class CreateSkillsetMutation(EnhancedClientIDMutation):
    @classmethod
    def __custom__(cls):
        create_insert_mutation(cls, SkillsetModel, SkillsetNode)


class UpdateSkillsetMutation(EnhancedClientIDMutation):
    @classmethod
    def __custom__(cls):
        create_update_mutation(cls, SkillsetModel, SkillsetNode)


class DeleteSkillsetMutation(EnhancedClientIDMutation):
    success = graphene.Field(graphene.Boolean)

    class Input:
        id = graphene.ID(required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        from ..mutations import get_id_from_node_id
        from bson import ObjectId
        node_id = input.get('id')
        id_ = get_id_from_node_id(node_id)
        skillsetObj = SkillsetModel.objects.get(pk=id_)
        psap_id = skillsetObj.psap_id
        for userObj in UserModel.objects(psap_id=psap_id):
            bson_id_ = ObjectId(id_)
            if  bson_id_ in userObj.skillsets:
                userObj.roles.remove(bson_id_)
                userObj.save()
        skillsetObj.delete()
        return DeleteSkillsetMutation(success=True)


class UpdateUserRolesMutation(graphene.relay.ClientIDMutation):
    user = graphene.Field(UserNode)

    class Input:
        user_id = graphene.String(required=True)
        roles = graphene.List(of_type=graphene.ID)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        user_id = input.get('user_id')
        log.info("user_id is %r", user_id)
        roles = []
        role_node_ids = input.get('roles')
        for role_node_id in role_node_ids:
            role_id = get_id_from_node_id(role_node_id)
            roles.append(role_id)
        userObj = UserModel.objects.get(user_id=user_id)
        userObj.roles = roles
        userObj.save()
        return userObj


class UpdateUserSkillsetsMutation(graphene.relay.ClientIDMutation):
    user = graphene.Field(UserNode)

    class Input:
        user_id = graphene.String(required=True)
        skillsets = graphene.List(of_type=graphene.ID)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        user_id = input.get('user_id')
        skillsets = []
        skillset_node_ids = input.get('skillsets')
        for skillset_node_id in skillset_node_ids:
            skillset_id = get_id_from_node_id(skillset_node_id)
            skillsets.append(skillset_id)
        userObj = UserModel.objects.get(user_id=user_id)
        userObj.skillsets = skillsets
        userObj.save()
        return userObj


