import graphene
from graphene import relay
from graphene_sqlalchemy import SQLAlchemyObjectType
from ...db.schema_sqlalchemy import Psap as PsapModel

class Psap(SQLAlchemyObjectType):
    class Meta:
        model = PsapModel
        interfaces = (relay.Node,)
        # use `only_fields` to only expose specific fields ie "name"
        # only_fields = ("name",)
        # use `exclude_fields` to exclude specific fields ie "last_name"
        # exclude_fields = ("last_name",)

