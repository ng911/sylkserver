import graphene
from graphene.relay import Node
from graphene_mongo import MongoengineConnectionField, MongoengineObjectType

from ..utiils import update_params_with_args
from ...applications. import User as UserModel
from .connection import DeviceConnectionNode
from .company import CompanyNode


class UserNode(MongoengineObjectType):
    class Meta:
        model = UserModel
        interfaces = (Node,)
    device_connections = MongoengineConnectionField(DeviceConnectionNode)

    def resolve_device_connections(parent, info, **args):
        params = {
            "userId" : parent.userId
        }
        params = update_params_with_args(params, args)
        return DeviceConnectionModel.objects(**params)




# Mutation to change bot name  and bot photo-url company specific
class RelayUserProfileMutation(graphene.relay.ClientIDMutation):
    company = graphene.Field(CompanyNode)

    class Input:
        profilePhoto = graphene.String()
        profileName = graphene.String()
        companyId = graphene.String()
        initialMessage = graphene.String()
    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        companyId = input.get('companyId')
        profileName = input.get('profileName')
        profilePhoto = input.get('profilePhoto')
        initialMessage = input.get('initialMessage')
        CompanyObj = CompanyModel.objects.get(companyId=companyId)
        CompanyObj.profileName = profileName
        CompanyObj.profilePhoto = profilePhoto
        CompanyObj.initialMessage = initialMessage
        CompanyObj.save()

        return RelayUserProfileMutation(company=CompanyObj)

class UserProfileMutation(graphene.AbstractType):
    relay_user_profile = RelayUserProfileMutation.Field()

