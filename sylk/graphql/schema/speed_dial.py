import graphene
from graphene import Field, String
from graphene.relay import Node
from graphene_mongo import MongoengineConnectionField, MongoengineObjectType

from ..utiils import update_params_with_args
from ...db.schema import SpeedDial as SpeedDialModel


class SpeedDialNode(MongoengineObjectType):
    class Meta:
        model = SpeedDialModel
        interfaces = (Node,)

