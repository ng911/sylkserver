import graphene
from graphene import Field, List, String
from graphene.relay import Node
from graphene_mongo import MongoengineConnectionField, MongoengineObjectType

from ..fields import EnhancedConnection
from ..utiils import update_params_with_args
from ...db.schema import Location as LocationModel


class LocationNode(MongoengineObjectType):
    class Meta:
        model = LocationModel
        interfaces = (Node,)
        connection_class = EnhancedConnection



