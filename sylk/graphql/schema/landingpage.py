from graphene.relay import Node
from graphene_mongo import MongoengineObjectType

from ...db.schema import LandingPage as LandingPageModel


class LandingPageNode(MongoengineObjectType):
    class Meta:
        model = LandingPageModel
        interfaces = (Node,)

