import arrow
from graphene import Field, List, String, ObjectType
from graphene.relay import Node
from graphene_mongo import MongoengineConnectionField, MongoengineObjectType

from ..fields import EnhancedConnection
from ..utiils import update_params_with_args
from ...db.schema import Conference as ConferenceModel
from ...db.schema import ConferenceEvent as EventLogModel
from ...db.schema import ConferenceParticipant as ConferenceParticipantModel
from ...db.schema import Location as LocationModel
from .location import LocationNode
from .event_log import EventLogNode
try:
    from sylk.applications import ApplicationLogger
    log = ApplicationLogger(__package__)
except:
    import logging
    log = logging.getLogger('emergent-ng911')

class ConferenceParticipantNode(MongoengineObjectType):
    class Meta:
        model = ConferenceParticipantModel
        interfaces = (Node,)


class ConferenceNode(MongoengineObjectType):
    class Meta:
        model = ConferenceModel
        interfaces = (Node,)
        connection_class = EnhancedConnection

    participants = MongoengineConnectionField(ConferenceParticipantNode)
    caller = Field(String)
    calltakers = List(String)
    latest_location = Field(LocationNode)
    locations = MongoengineConnectionField(LocationNode)
    event_logs = MongoengineConnectionField(EventLogNode)

    def resolve_participants(parent, info, **args):
        params = {
            "room_number" : parent.room_number
        }
        params = update_params_with_args(params, args)
        return ConferenceParticipantModel.objects(**params)

    def resolve_event_logs(parent, info, **args):
        params = {
            "room_number" : parent.room_number
        }
        params = update_params_with_args(params, args)
        return EventLogModel.objects(**params)

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

def resolveActiveCall(parent, info, **args):
    username = args['username']
    # there should only be 1 value in rooms but there is some bug in the code, that is why the logic below
    rooms = []
    for dbObj in ConferenceParticipantModel.objects(is_calltaker=True, is_active=True, name=username):
        rooms.append(dbObj.room_number)
    return ConferenceModel.objects(room_number__in=[rooms], status="active").first()

def resolveCalls(parent, info, **args):
    from bson import ObjectId
    calling_number = None
    location = None
    note = None
    start_time = None
    end_time = None
    if 'psap_id' in args:
        psap_id = args['psap_id']
    if 'calling_number' in args:
        calling_number = args['calling_number']
    if 'location' in args:
        location = args['location']
    if 'note' in args:
        note = args['note']
    if 'start_time' in args:
        start_time = args['start_time']
    if 'end_time' in args:
        end_time = args['end_time']

    filters = {'psap_id': ObjectId(psap_id),
               'status': {'$nin': ['active', 'init', 'ringing', 'on_hold', 'queued', 'ringing_queued']}}
    if (calling_number != None) and (len(calling_number) > 0):
        log.info('inside search calling_number %s', calling_number)
        filters['caller_ani'] = {'$regex': calling_number, '$options': 'i'}
    if (location != None) and (len(location) > 0):
        log.info('inside search location %s', location)
        filters['location_display'] = {'$regex': location, '$options': 'i'}
    if (note != None) and (len(note) > 0):
        log.info('inside search note %s', note)
        filters['note'] = {'$regex': note, '$options': 'i'}
    if (start_time != None) and (end_time != None) and (len(start_time) > 0) and (len(end_time) > 0):
        log.info("start_time is %r", start_time)
        log.info("end_time is %r", end_time)
        arrow_start = arrow.get(start_time)
        arrow_end = arrow.get(end_time)
        complex_time_format = 'YYYY,MM,DD,HH,mm,ss,SSSSSS'
        formatted_start_time = arrow_start.format(complex_time_format)
        formatted_end_time = arrow_end.format(complex_time_format)
        filters['start_time'] = {'$gte': formatted_start_time,
                                 '$lt': formatted_end_time}
    log.info("inside call search filters is %r", filters)
    return ConferenceModel.objects(__raw__=filters).order_by('-start_time')
