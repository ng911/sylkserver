from graphene.relay import Node
from graphene_mongo import MongoengineConnectionField, MongoengineObjectType

from ..utiils import update_params_with_args
from ...db.schema import Agent as AgentModel
from ...db.schema import DeviceConnection as DeviceConnectionModel
from .connection import DeviceConnectionNode


class AgentNode(MongoengineObjectType):
    class Meta:
        model = AgentModel
        interfaces = (Node,)
    device_connections = MongoengineConnectionField(DeviceConnectionNode)

    def resolve_device_connections(parent, info, **args):
        params = {
            "userId" : parent.userId
        }
        params = update_params_with_args(params, args)
        return DeviceConnectionModel.objects(**params)


