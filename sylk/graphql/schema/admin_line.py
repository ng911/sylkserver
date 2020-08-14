import graphene
from graphene import Field, String
from graphene.relay import Node
from graphene_mongo import MongoengineConnectionField, MongoengineObjectType

from ..fields import EnhancedConnection
from ..utiils import update_params_with_args
from ...db.schema import AdminLine as AdminLineModel
from ...db.schema import AdminLineGroup as AdminLineGroupModel


class AdminLineNode(MongoengineObjectType):
    class Meta:
        model = AdminLineModel
        interfaces = (Node,)
        connection_class = EnhancedConnection


class AdminLineGroupNode(MongoengineObjectType):
    class Meta:
        model = AdminLineGroupModel
        interfaces = (Node,)
        connection_class = EnhancedConnection

    admin_lines = MongoengineConnectionField(AdminLineNode)

    def resolve_admin_lines(parent, info, **args):
        return AdminLineModel.objects(group_id = parent.group_id)

from ..mutations import create_insert_mutation, create_update_mutation, create_delete_mutation, \
    EnhancedClientIDMutation


class CreteAdminLineMutation(EnhancedClientIDMutation):
    @classmethod
    def __custom__(cls):
        create_insert_mutation(cls, AdminLineModel, AdminLineNode)


class UpdateAdminLineMutation(EnhancedClientIDMutation):
    @classmethod
    def __custom__(cls):
        create_update_mutation(cls, AdminLineModel, AdminLineNode, 'admin_line_id')


class DeleteAdminLineMutation(EnhancedClientIDMutation):
    @classmethod
    def __custom__(cls):
        create_delete_mutation(cls, AdminLineModel)


class CreteAdminLineGroupMutation(EnhancedClientIDMutation):
    @classmethod
    def __custom__(cls):
        create_insert_mutation(cls, AdminLineGroupModel, AdminLineGroupNode)


class UpdateAdminLineGroupMutation(EnhancedClientIDMutation):
    @classmethod
    def __custom__(cls):
        create_update_mutation(cls, AdminLineGroupModel, AdminLineGroupNode, 'group_id')


class DeleteAdminLineGroupMutation(EnhancedClientIDMutation):
    success = graphene.Boolean()

    class Input:
        group_id = graphene.String(required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        group_id = input.get('group_id')
        try:
            AdminLineModel.objects(group_id=group_id).delete()
            AdminLineGroupModel.objects(group_id=group_id).delete()
        except Exception as e:
            return False
        return True

