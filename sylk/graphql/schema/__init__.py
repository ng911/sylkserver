import graphene
from graphene.relay import Node
from graphene_mongo import MongoengineConnectionField

from ..fields import OrderedMongoengineConnectionField, MongoengineObjectType
from .user import UserNode, UpdateUserMutation, resolveUserGroups
from .psap import PsapNode, CreatePsapMutation, UpdatePsapMutation
from .queue import QueueNode
from .speed_dial import SpeedDialNode, SpeedDialGroupNode
from .calls import ConferenceNode, resolveCalls, resolveActiveCall
from ..decorators import subsribe_for_node, subsribe_for_connection
from ...db.schema import User as UserModel
from .user import PsapUsersNode, UserPermissionNode, UserRoleNode, UserGroupNode
from .calls import PsapConferenceNode
from ...db.schema import Conference as ConferenceModel
from .message import MessageNode, PsapMessageNode
from ...db.schema import ConferenceMessage as ConferenceMessageModel
from .admin_line import AdminLineNode, AdminLineGroupNode
from .admin_line import CreteAdminLineGroupMutation, CreteAdminLineMutation
from .admin_line import UpdateAdminLineGroupMutation, UpdateAdminLineMutation
from .admin_line import DeleteAdminLineGroupMutation, DeleteAdminLineMutation
from .admin_line import resolveAdminLineServers

try:
    from sylk.applications import ApplicationLogger
    log = ApplicationLogger(__package__)
except:
    import logging
    log = logging.getLogger('emergent-ng911')


class Query(graphene.ObjectType):
    node = Node.Field()
    all_messages = OrderedMongoengineConnectionField(MessageNode)
    all_users = OrderedMongoengineConnectionField(UserNode)
    psap_user_roles = OrderedMongoengineConnectionField(UserRoleNode)
    psap_user_groups = graphene.Field(graphene.List(of_type=graphene.String), psap_id=graphene.String(required=True))
    all_psaps = OrderedMongoengineConnectionField(PsapNode)
    all_queues = OrderedMongoengineConnectionField(QueueNode)
    all_speed_dials = OrderedMongoengineConnectionField(SpeedDialNode)
    all_speed_dial_groups = OrderedMongoengineConnectionField(SpeedDialGroupNode)
    all_admin_lines = OrderedMongoengineConnectionField(AdminLineNode)
    all_admin_line_groups = OrderedMongoengineConnectionField(AdminLineGroupNode)
    admin_line_servers = graphene.Field(graphene.List(of_type=graphene.String), psap_id=graphene.String(required=True))
    all_conferences = OrderedMongoengineConnectionField(ConferenceNode, \
                                                        calling_number=graphene.String(required=False), \
                                                        location=graphene.String(required=False))
    # active call for a calltaker
    active_call = graphene.Field(ConferenceNode, username=graphene.String(required=True))

    def resolve_active_call(parent, info, **args):
        return resolveActiveCall(parent, info, **args)

    def resolve_admin_line_servers(parent, info, **args):
        return resolveAdminLineServers(parent, info, **args)

    def resolve_user_groups(parent, info, **args):
        return resolveUserGroups(parent, info, **args)


class Subscriptions(graphene.ObjectType):
    user_data = graphene.Field(UserNode, username=graphene.String(required=True))
    psap_users = graphene.Field(PsapUsersNode)
    psap_calls = graphene.Field(PsapConferenceNode)
    call_data = graphene.Field(ConferenceNode, room_number=graphene.String(required=True))
    message_data = graphene.Field(MessageNode, room_number=graphene.String(required=True))
    psap_messages = graphene.Field(PsapMessageNode)
    new_call = graphene.Field(ConferenceNode)
    all_calls = MongoengineConnectionField(ConferenceNode)

    @subsribe_for_node(PsapUsersNode)
    async def resolve_user_data(root, info, **args):
        pass

    @subsribe_for_connection(PsapUsersNode, UserModel)
    async def resolve_psap_users(root, info, **args):
        pass

    @subsribe_for_node(ConferenceNode)
    async def resolve_call_data(root, info, **args):
        pass

    @subsribe_for_node(ConferenceNode, is_new=True)
    async def resolve_new_call(root, info, **args):
        pass

    @subsribe_for_connection(ConferenceNode, ConferenceModel)
    async def resolve_psap_calls(root, info, **args):
        pass

    @subsribe_for_connection(ConferenceNode, ConferenceModel, experimantal=True)
    async def resolve_all_calls(root, info, **args):
        #return ConferenceModel.objects()
        pass

    @subsribe_for_node(MessageNode)
    async def resolve_message_data(root, info, **args):
        pass

    @subsribe_for_connection(MessageNode, ConferenceMessageModel)
    async def resolve_psap_messages(root, info, **args):
        pass


class Mutations(graphene.ObjectType):
    update_user = UpdateUserMutation.Field()
    create_psap = CreatePsapMutation.Field()
    update_psap = UpdatePsapMutation.Field()
    create_adminline_group = CreteAdminLineGroupMutation.Field()
    create_adminline = CreteAdminLineMutation.Field()
    update_adminline_group = UpdateAdminLineGroupMutation.Field()
    update_adminline = UpdateAdminLineMutation.Field()
    delete_adminline_group = DeleteAdminLineGroupMutation.Field()
    delete_adminline = DeleteAdminLineMutation.Field()


graphene_schema = graphene.Schema(query=Query, mutation=Mutations, subscription=Subscriptions, types=[])

__all__ = [ 'graphene_schema']

