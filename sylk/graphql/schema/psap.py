import graphene
from graphene import Field, String, List
from graphene.relay import Node
from graphene_mongo import MongoengineConnectionField, MongoengineObjectType

from ..fields import EnhancedConnection
from ..utiils import update_params_with_args
from ...db.schema import Psap as PsapModel
from ...db.schema import User as UserModel
from ...db.schema import CalltakerProfile as CalltakerProfileModel
from ...db.schema import SpeedDial as SpeedDialModel
from .user import UserNode, UserProfileNode
from .speed_dial import SpeedDialNode
from .calls import ConferenceNode
from ...db.schema import Conference as ConferenceModel
from ...db.schema import CallTransferLine as CallTransferLineModel


class CallTransferLineNode(MongoengineObjectType):
    class Meta:
        model = CallTransferLineModel
        interfaces = (Node,)
        connection_class = EnhancedConnection


class PsapNode(MongoengineObjectType):
    class Meta:
        model = PsapModel
        interfaces = (Node,)
        connection_class = EnhancedConnection

    users = MongoengineConnectionField(UserNode)
    default_profile = Field(UserProfileNode)
    speed_dials = MongoengineConnectionField(SpeedDialNode)
    speed_dial_groups = List(String)
    conferences = MongoengineConnectionField(ConferenceNode)
    transfer_lines = MongoengineConnectionField(CallTransferLineNode)

    def resolve_users(parent, info, **args):
        params = {
            "psap_id" : parent.psap_id
        }
        params = update_params_with_args(params, args)
        return UserModel.objects(**params)

    def resolve_default_profile(parent, info, **args):
        params = {
            "psap_id" : parent.psap_id
        }
        return CalltakerProfileModel.objects.get(**params)

    def resolve_speed_dials(parent, info, **args):
        params = {
            "psap_id" : parent.psap_id
        }
        return SpeedDialModel.objects(**params)

    def resolve_conferences(parent, info, **args):
        params = {
            "psap_id" : parent.psap_id
        }
        params = update_params_with_args(params, args)
        return ConferenceModel.objects(**params)

    def resolve_speed_dial_groups(parent, info, **args):
        params = {
            "psap_id" : parent.psap_id
        }
        speed_dial_groups = []
        for speedDial in SpeedDialModel.objects(**params):
            if hasattr(speedDial, "group") and (speedDial.group != ""):
                speed_dial_groups.append(speedDial.group)

        return speed_dial_groups

    def resolve_transfer_lines(parent, info, **args):
        params = {
            "psap_id" : parent.psap_id
        }
        params = update_params_with_args(params, args)
        return CallTransferLineModel.objects(**params)


class CreatePsapMutation(graphene.relay.ClientIDMutation):
    psap = graphene.Field(PsapNode)

    class Input:
        name = graphene.String(required=True)
        domain_prefix = graphene.String(required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        name = input.get('name')
        domain_prefix = input.get('domain_prefix')
        psapObj = PsapModel(name=name, domain=domain_prefix)
        psapObj.save()
        return CreatePsapMutation(psap=psapObj)


class UpdatePsapMutation(graphene.relay.ClientIDMutation):
    psap = graphene.Field(PsapNode)

    class Input:
        psap_id = graphene.String(required=True)
        name = graphene.String()
        domain_prefix = graphene.String()
        name = graphene.String()
        time_to_autorebid = graphene.Int()
        auto_rebid = graphene.Boolean()
        cad_listen_port = graphene.Int()
        auto_rebid_time = graphene.Int()
        sos_call_handling = graphene.String()
        sos_acd = graphene.String()
        enable_overflow_handling = graphene.Boolean()
        max_calls_in_queue = graphene.Int()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        psap_id = input.get('psap_id')
        name = input.get('name')
        domain_prefix = input.get('domain_prefix')
        psapObj = PsapModel.objects.get(psap_id=psap_id)
        if name != None:
            psapObj.name = name
        if domain_prefix != None:
            psapObj.domain = domain_prefix

        time_to_autorebid = input.get('time_to_autorebid')
        if time_to_autorebid != None:
            psapObj.time_to_autorebid = time_to_autorebid

        auto_rebid = input.get('auto_rebid')
        if auto_rebid != None:
            psapObj.auto_rebid = auto_rebid

        auto_rebid_time = input.get('auto_rebid_time')
        if auto_rebid_time != None:
            psapObj.auto_rebid_time = auto_rebid_time

        cad_listen_port = input.get('cad_listen_port')
        if cad_listen_port != None:
            psapObj.cad_listen_port = cad_listen_port

        sos_call_handling = input.get('sos_call_handling')
        if sos_call_handling != None:
            psapObj.sos_call_handling = sos_call_handling

        sos_acd = input.get('sos_acd')
        if sos_acd != None:
            psapObj.sos_acd = sos_acd

        enable_overflow_handling = input.get('enable_overflow_handling')
        if enable_overflow_handling != None:
            psapObj.enable_overflow_handling = enable_overflow_handling

        max_calls_in_queue = input.get('max_calls_in_queue')
        if max_calls_in_queue != None:
            psapObj.max_calls_in_queue = max_calls_in_queue

        psapObj.save()
        return UpdatePsapMutation(psap=psapObj)

from ..mutations import create_insert_mutation, create_update_mutation, create_delete_mutation, \
    EnhancedClientIDMutation

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
