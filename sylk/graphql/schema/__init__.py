import graphene
from graphene.relay import Node
from graphene_mongo import MongoengineConnectionField

from ..fields import OrderedMongoengineConnectionField, MongoengineObjectType
from .user import UserNode, UpdateUserMutation, resolveUserGroups, \
                CreateRoleMutation, UpdateRoleMutation, DeleteRoleMutation, \
                CreateSkillsetMutation, UpdateSkillsetMutation, DeleteSkillsetMutation, \
                CreateUserMutation, UpdateUserRolesMutation, UpdateUserSkillsetsMutation

from .psap import PsapNode, CreatePsapMutation, UpdatePsapMutation
from .queue import QueueNode
from .speed_dial import SpeedDialNode, SpeedDialGroupNode
from .calls import ConferenceNode, resolveCalls, resolveActiveCall
from ..decorators import subsribe_for_node, subsribe_for_connection
from ...db.schema import User as UserModel
from .user import PsapUsersNode, UserPermissionNode, UserGroupNode, RoleNode, SkillsetNode
from .calls import PsapConferenceNode
from ...db.schema import Conference as ConferenceModel
from .message import MessageNode, PsapMessageNode
from ...db.schema import ConferenceMessage as ConferenceMessageModel
from ...db.schema import AdminLineGroup as AdminLineGroupModel
from ...db.schema import AdminLine as AdminLineModel
from .admin_line import AdminLineNode, AdminLineGroupNode
from .admin_line_subscription import PsapAdminLineGroupsNode, PsapAdminLinesNode
from .admin_line import CreteAdminLineGroupMutation, CreteAdminLineMutation
from .admin_line import UpdateAdminLineGroupMutation, UpdateAdminLineMutation
from .admin_line import DeleteAdminLineGroupMutation, DeleteAdminLineMutation
from .admin_line import resolveAdminLineServers
from .maps import MapLayerNode, MapFileNode
from .routing import CallTransferLineNode
from .routing import CreateCallTransferLineMutation, UpdateCallTransferLineMutation, DeleteCallTransferLineMutation
from .prompt import VoicePromptNode
from .prompt import CreateVoicePromptMutation, UpdateVoicePromptMutation, DeleteVoicePromptMutation


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
    psap_user_roles = OrderedMongoengineConnectionField(RoleNode)
    psap_skillsets = OrderedMongoengineConnectionField(SkillsetNode)
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
    all_map_files = OrderedMongoengineConnectionField(MapFileNode)
    all_map_layers = OrderedMongoengineConnectionField(MapLayerNode)
    all_call_transfer_lines = OrderedMongoengineConnectionField(CallTransferLineNode)
    all_voice_prompts = OrderedMongoengineConnectionField(VoicePromptNode)
    # active call for a calltaker
    active_call = graphene.Field(ConferenceNode, username=graphene.String(required=True))

    def resolve_active_call(parent, info, **args):
        return resolveActiveCall(parent, info, **args)

    def resolve_admin_line_servers(parent, info, **args):
        return resolveAdminLineServers(parent, info, **args)

    def resolve_psap_user_groups(parent, info, **args):
        return resolveUserGroups(parent, info, **args)

from .admin_line_subscription import PsapActiveAdminLinesNode

class Subscriptions(graphene.ObjectType):
    user_data = graphene.Field(UserNode, username=graphene.String(required=True))
    psap_users = graphene.Field(PsapUsersNode)
    psap_calls = graphene.Field(PsapConferenceNode)
    call_data = graphene.Field(ConferenceNode, room_number=graphene.String(required=True))
    message_data = graphene.Field(MessageNode, room_number=graphene.String(required=True))
    psap_messages = graphene.Field(PsapMessageNode)
    new_call = graphene.Field(ConferenceNode)
    #all_calls = MongoengineConnectionField(ConferenceNode)
    psap_admin_line_groups = graphene.Field(PsapAdminLineGroupsNode, psap_id=graphene.String(required=True))
    psap_admin_lines = graphene.Field(PsapAdminLinesNode, psap_id=graphene.String(required=True), \
                                      group_id=graphene.String(required=False))
    psap_active_admin_lines = graphene.Field(PsapActiveAdminLinesNode, psap_id=graphene.String(required=True))
    '''
    add one by one
    psap_admin_lines = MongoengineConnectionField(PsapAdminLineNode)
    psap_active_911_calls = MongoengineConnectionField(PsapActive911Call)
    psap_active_admin_calls = MongoengineConnectionField(PsapActiveAdminCalls)
    psap_recent_calls = MongoengineConnectionField(PsapRecentCalls)
    user_recent_calls = MongoengineConnectionField(UserRecentCalls)
    '''

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

    @subsribe_for_connection(PsapActiveAdminLinesNode, ConferenceModel)
    async def resolve_psap_active_admin_lines(root, info, **args):
        pass
    '''
    enable later 
    @subsribe_for_connection(ConferenceNode, ConferenceModel, experimantal=True)
    async def resolve_all_calls(root, info, **args):
        #return ConferenceModel.objects()
        pass
    '''

    @subsribe_for_node(MessageNode)
    async def resolve_message_data(root, info, **args):
        pass

    @subsribe_for_connection(MessageNode, ConferenceMessageModel)
    async def resolve_psap_messages(root, info, **args):
        pass

    @subsribe_for_connection(PsapAdminLineGroupsNode, AdminLineGroupModel)
    async def resolve_psap_admin_line_groups(root, info, **args):
        pass

    @subsribe_for_connection(PsapAdminLinesNode, AdminLineModel)
    async def resolve_psap_admin_lines(root, info, **args):
        pass


def test_resolve():
    log.info("inside test_resolve")
    #up_to = 10
    #for i in range(up_to):
    #    yield PsapAdminLinesNode()

class Mutations(graphene.ObjectType):
    create_user = CreateUserMutation.Field()
    update_user = UpdateUserMutation.Field()
    create_psap = CreatePsapMutation.Field()
    update_psap = UpdatePsapMutation.Field()
    create_adminline_group = CreteAdminLineGroupMutation.Field()
    create_adminline = CreteAdminLineMutation.Field()
    update_adminline_group = UpdateAdminLineGroupMutation.Field()
    update_adminline = UpdateAdminLineMutation.Field()
    delete_adminline_group = DeleteAdminLineGroupMutation.Field()
    delete_adminline = DeleteAdminLineMutation.Field()
    update_user_roles = UpdateUserRolesMutation.Field()
    update_user_skillsets = UpdateUserSkillsetsMutation.Field()
    create_role = CreateRoleMutation.Field()
    update_role = UpdateRoleMutation.Field()
    delete_role = DeleteRoleMutation.Field()
    create_skillset = CreateSkillsetMutation.Field()
    update_skillset = UpdateSkillsetMutation.Field()
    delete_skillset = DeleteSkillsetMutation.Field()
    create_call_transfer_line = CreateCallTransferLineMutation.Field()
    update_call_transfer_line = UpdateCallTransferLineMutation.Field()
    delete_call_transfer_line = DeleteCallTransferLineMutation.Field()
    create_voice_prompt = CreateVoicePromptMutation.Field()
    update_voice_prompt = UpdateVoicePromptMutation.Field()
    delete_voice_prompt = DeleteVoicePromptMutation.Field()


graphene_schema = graphene.Schema(query=Query, mutation=Mutations, subscription=Subscriptions, types=[])

__all__ = [ 'graphene_schema']

