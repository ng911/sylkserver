from graphene.relay import Node
from graphene.types import String, Field
from graphene_mongo import MongoengineConnectionField, MongoengineObjectType

from ..utiils import update_params_with_args
from ...db.schema import MailgunEmailEvent as EmailEventModel
from ...db.schema import Email as EmailModel
from ...db.schema import User as UserModel
from .user import UserNode

class EmailEventNode(MongoengineObjectType):
    class Meta:
        model = EmailEventModel
        interfaces = (Node,)


class EmailNode(MongoengineObjectType):
    class Meta:
        model = EmailModel
        interfaces = (Node,)

    user = Field(UserNode)
    events = MongoengineConnectionField(EmailEventNode)

    def resolve_user(parent, info):
        try:
            return UserModel.objects.get(userId=parent.userId)
        except:
            return None

    def resolve_events(parent, info, **args):
        params = {
            "mgId" : parent.messageId
        }
        params = update_params_with_args(params, args)
        return EmailEventModel.objects(**params)


