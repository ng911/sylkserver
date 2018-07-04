import traceback
import datetime
from bson import ObjectId
import arrow
from sylk.applications import ApplicationLogger
from sylk.db.schema import ConferenceEvent, ConferenceParticipant, Location, Conference
from sylk.utils import get_json_from_db_obj
import location
from sylk.configuration import ServerConfig

log = ApplicationLogger(__package__)

ignore_conference_fields = [
    'psap_id', 'type1', 'type2', 'pictures', 'primary_queue_id', 'secondary_queue_id', 'link_id'
]

def get_conference_participants_json(room_number):
    participants = []
    for participant_db_obj in ConferenceParticipant.objects(room_number=room_number):
        participant_json = get_json_from_db_obj(participant_db_obj)
        participants.append(participant_json)
    return participants


def get_active_calltakers(room_number):
    active_calltakers = []
    for participant_db_obj in ConferenceParticipant.objects(room_number=room_number):
        if participant_db_obj.is_active and participant_db_obj.is_calltaker:
            active_calltakers.append(participant_db_obj.name)
    return active_calltakers

def get_active_participants(room_number):
    active_participants = []
    for participant_db_obj in ConferenceParticipant.objects(room_number=room_number):
        if participant_db_obj.is_active:
            active_participants.append(participant_db_obj.name)
    return active_participants

def get_conference_event_log_json(room_number):
    events = []
    for event_db_obj in ConferenceEvent.objects(room_number=room_number):
        event_json = get_json_from_db_obj(event_db_obj)
        events.append(event_json)
    return events


def get_conference_duration(conference_db_obj):
    if conference_db_obj.status == 'active':
        cur_time = arrow.utcnow()
        start_time = arrow.get(conference_db_obj.answer_time)
        time_diff = cur_time - start_time
        return int(time_diff.total_seconds())
    elif conference_db_obj.status == 'closed':
        end_time = arrow.get(conference_db_obj.end_time)
        start_time = arrow.get(conference_db_obj.answer_time)
        time_diff = end_time - start_time
        return int(time_diff.total_seconds())
    return 0


def get_conference_json(conference_db_obj):
    conference_json = get_json_from_db_obj(conference_db_obj, ignore_fields=ignore_conference_fields)
    conference_json['location'] = get_location_for_call(conference_db_obj.room_number)
    conference_json['duration'] = get_conference_duration(conference_db_obj)
    conference_json['active_calltakers'] = get_active_calltakers(conference_db_obj.room_number)
    conference_json['active_participants'] = get_active_participants(conference_db_obj.room_number)

    return conference_json


def get_location_for_call(room_number):
    try:
        location_db_obj = Location.objects(room_number=room_number).order_by('-updated_at').first()
        if location_db_obj is not None:
            return location.get_location_display(location_db_obj)
        return ''
    except Exception as e:
        stacktrace = traceback.format_exc()
        log.error("exception in get_location_for_call for room %r, e %r", room_number, str(e))
        log.error("%r", stacktrace)
        return ""


def clear_abandoned_calls(callback_number=None, caller_ani=None):
    filters = {'psap_id': ObjectId(ServerConfig.psap_id),
               'callback' : False,
               'status' : 'abandoned',
               'call_type' : 'sos'}

    if callback_number is not None:
       filters['callback_number'] = callback_number
    elif caller_ani is not None:
        filters['caller_ani'] = caller_ani
    else:
        log.error("clear_abandoned_calls no callback_number or caller_ani")
        return

    for conf_db_obj in Conference.objects(__raw__=filters):
        conf_db_obj.callback_time = datetime.datetime.utcnow
        conf_db_obj.callback = True
        conf_db_obj.save()

'''
def clear_abandoned_calls(called_number):
    filters = {'psap_id': ObjectId(ServerConfig.psap_id),
               'callback' : False,
               'status' : 'abandoned',
               'call_type' : 'sos',
               'or': [{'caller_ani': called_number}, {'callback_number': called_number}]}

    for conf_db_obj in Conference.objects(__raw__=filters):
        conf_db_obj.callback_time = datetime.datetime.utcnow
        conf_db_obj.callback = True
        conf_db_obj.save()
'''

