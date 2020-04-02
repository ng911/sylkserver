from graphene.relay import Node
from graphene_mongo import MongoengineObjectType

from ...db.schema import DeviceConnection as DeviceConnectionModel

class DeviceConnectionNode(MongoengineObjectType):
    class Meta:
        model = DeviceConnectionModel
        interfaces = (Node,)



