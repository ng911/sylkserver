import traceback
import graphene
from graphene import Field, String
from graphene.relay import Node
from graphene_mongo import MongoengineConnectionField, MongoengineObjectType

from ..fields import EnhancedConnection, OrderedMongoengineConnectionField
from ..utiils import update_params_with_args, update_params_for_subscriptions
from ...db.schema import AdminLine as AdminLineModel
from ...db.schema import AdminLineGroup as AdminLineGroupModel
try:
    from sylk.applications import ApplicationLogger
    log = ApplicationLogger(__package__)
except:
    import logging
    log = logging.getLogger('emergent-ng911')


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


class PsapAdminLineGroupsNode(graphene.ObjectType):
    '''
    Used for subscriptions
    '''
    class Meta:
        interfaces = (Node,)
    admin_line_groups = OrderedMongoengineConnectionField(AdminLineGroupNode)

    @classmethod
    def get_node(cls, info, id):
        return f"PsapAdminLineGroupsNode{id}"

    def resolve_admin_line_groups(parent, info, **args):
        params = {}
        update_params_for_subscriptions(params, parent)
        update_params_with_args(params, args)
        return AdminLineGroupModel.objects(**params)

from ...db.schema import Conference as ConferenceModel
from .calls import ConferenceNode

class PsapActiveAdminLinesNode(graphene.ObjectType):
    '''
    Used for subscriptions
    '''
    class Meta:
        interfaces = (Node,)
    active_admin_lines = OrderedMongoengineConnectionField(ConferenceNode)

    @classmethod
    def get_node(cls, info, id):
        return f"PsapActiveAdminLinesNode{id}"

    def resolve_active_admin_lines(parent, info, **args):
        params = {"call_type__in" : ["admin"]}
        update_params_for_subscriptions(params, parent)
        update_params_with_args(params, args)
        return ConferenceModel.objects(**params)


class PsapAdminLinesNode(graphene.ObjectType):
    '''
    Used for subscriptions
    '''
    class Meta:
        interfaces = (Node,)
    admin_lines = OrderedMongoengineConnectionField(AdminLineNode)

    @classmethod
    def get_node(cls, info, id):
        return f"PsapAdminLinesNode{id}"

    def resolve_admin_lines(parent, info, **args):
        params = {}
        update_params_for_subscriptions(params, parent)
        update_params_with_args(params, args)
        return AdminLineModel.objects(**params)


def resolveAdminLineServers(parent, info, **args):
    psap_id = args['psap_id']
    # there should only be 1 value in rooms but there is some bug in the code, that is why the logic below
    servers = []
    for dbObj in AdminLineModel.objects(psap_id=psap_id):
        if hasattr(dbObj, 'server') and dbObj.server != None and dbObj.server != '':
            server = dbObj.server.strip()
            if server != '' and server not in servers:
                servers.append(server)
    return servers


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
        id = graphene.ID(required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        from ..mutations import get_id_from_node_id
        node_id = input.get('id')
        try:
            id_ = get_id_from_node_id(node_id)
            groupObj = AdminLineGroupModel.objects.get(pk=id_)
            group_id = groupObj.group_id
            AdminLineModel.objects(group_id=group_id).delete()
            AdminLineGroupModel.objects(group_id=group_id).delete()
            return DeleteAdminLineGroupMutation(success=True)
        except Exception as e:
            stacktrace = traceback.format_exc()
            log.error(stacktrace)
            log.error(str(e))
            return DeleteAdminLineGroupMutation(success=False)

