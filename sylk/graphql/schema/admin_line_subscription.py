import graphene
from graphene.relay import Node

from ..fields import OrderedMongoengineConnectionField
from ..utiils import update_params_with_args, update_params_for_subscriptions
from ...db.schema import Conference as ConferenceModel
from .calls import ConferenceNode
from .admin_line import AdminLineNode, AdminLineGroupNode
from ...db.schema import AdminLine as AdminLineModel
from ...db.schema import AdminLineGroup as AdminLineGroupModel

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
        params = {
            "call_type__in" : ["admin"],
            "status__in" : ['init', 'ringing', 'ringing_queued', 'queued', 'active', 'on_hold'],
        }
        update_params_for_subscriptions(params, parent)
        update_params_with_args(params, args)
        return ConferenceModel.objects(**params)


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

