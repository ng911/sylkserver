import graphene
from graphene import Field, List, String, ObjectType
from graphene.relay import Node
from graphene_mongo import MongoengineConnectionField, MongoengineObjectType

from ..fields import EnhancedConnection
from ..utiils import update_params_with_args
from ...db.schema import Conference as ConferenceModel
from ...db.schema import Conference1 as Conference1Model
from ...db.schema import ConferenceParticipant as ConferenceParticipantModel
from ...db.schema import Location as LocationModel
from .location import LocationNode


class ConferenceParticipantNode(MongoengineObjectType):
    class Meta:
        model = ConferenceParticipantModel
        interfaces = (Node,)


class ConferenceNode(MongoengineObjectType):
    class Meta:
        model = ConferenceModel
        interfaces = (Node,)
        #connection_class = EnhancedConnection

    '''
    participants = MongoengineConnectionField(ConferenceParticipantNode)
    caller = Field(String)
    calltakers = List(String)
    latest_location = Field(LocationNode)
    locations = MongoengineConnectionField(LocationNode)

    def resolve_participants(parent, info, **args):
        params = {
            "room_number" : parent.room_number
        }
        params = update_params_with_args(params, args)
        return ConferenceParticipantModel.objects(**params)

    def resolve_caller(parent, info):
        params = {
            "room_number" : parent.room_number,
            "is_caller" : True
        }
        return ConferenceParticipantModel.objects.get(**params).name

    def resolve_calltakers(parent, info):
        params = {
            "room_number" : parent.room_number,
            "is_calltaker": True
        }
        calltakers = []
        for participant in ConferenceParticipantModel.objects(**params):
            if participant.name not in calltakers:
                calltakers.append(participant.name)
        return calltakers
    
    def resolve_latest_location(parent, info):
        params = {
            "room_number": parent.room_number
        }
        return LocationModel.objects(**params).order_by('-updated_at').first()

    def resolve_locations(parent, info, **args):
        params = {
            "room_number": parent.room_number
        }
        params = update_params_with_args(params, args)
        return LocationModel.objects(**params).order_by('-updated_at')
    '''

