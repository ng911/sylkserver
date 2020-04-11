import graphene
from graphene import Field, String, List
from graphene.relay import Node
from graphene_mongo import MongoengineConnectionField, MongoengineObjectType

from ..utiils import update_params_with_args
from ...db.schema import Psap as PsapModel
from ...db.schema import User as UserModel
from ...db.schema import CalltakerProfile as CalltakerProfileModel
from ...db.schema import SpeedDial as SpeedDialModel
from .user import UserNode, UserProfileNode
from .speed_dial import SpeedDialNode
from .calls import ConferenceNode
from ...db.schema import Conference as ConferenceModel
from ...db.schema import Conference1 as Conference1Model


class PsapNode(MongoengineObjectType):
    class Meta:
        model = PsapModel
        interfaces = (Node,)

    users = MongoengineConnectionField(UserNode)
    default_profile = Field(UserProfileNode)
    speed_dials = MongoengineConnectionField(SpeedDialNode)
    speed_dial_groups = List(String)
    conferences = MongoengineConnectionField(ConferenceNode)

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
        return Conference1Model.objects(**params)

    def resolve_speed_dial_groups(parent, info, **args):
        params = {
            "psap_id" : parent.psap_id
        }
        speed_dial_groups = []
        for speedDial in SpeedDialModel.objects(**params):
            if hasattr(speedDial, "group") and (speedDial.group != ""):
                speed_dial_groups.append(speedDial.group)

        return speed_dial_groups

