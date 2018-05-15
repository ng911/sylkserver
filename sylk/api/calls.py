import traceback
import datetime
import arrow
from flask import Blueprint, jsonify, request, send_from_directory
from flask_cors import CORS
from sylk.applications import ApplicationLogger
from sylk.db.schema import Conference, ConferenceEvent, ConferenceParticipant, Call, Location
from application.notification import NotificationCenter, NotificationData
from sylk.utils import get_json_from_db_obj, set_db_obj_from_request, copy_request_data_to_object
from sylk.api.location import get_location_display
from utils import get_argument
from mongoengine import Q

calls = Blueprint('calls', __name__,
                        template_folder='templates')

CORS(calls)
log = ApplicationLogger(__package__)

ignore_conference_fields = [
    'psap_id', 'type1', 'type2', 'pictures', 'primary_queue_id', 'secondary_queue_id', 'link_id'
]

'''
Note - for now we ignore the psap_id
returns currently active calls
'''
@calls.route('/', methods=['GET'])
def current():
    log.info("get current calls")
    calls = []
    for conference_db_obj in Conference.objects(Q(status__in=['init', 'ringing', 'ringing_queued', 'queued', 'active']) | (Q(status='abandoned') & Q(callback=False))):
        conference_json = get_json_from_db_obj(conference_db_obj, ignore_fields=ignore_conference_fields)
        #todo - get actual location
        conference_json['location'] = get_location_for_call(conference_db_obj.room_number)
        conference_json['participants'] = get_conference_participants_json(conference_db_obj.room_number)
        conference_json['event_log'] = get_conference_event_log_json(conference_db_obj.room_number)
        calls.append(conference_json)
    response = {
        'success' : True,
        'calls' : calls
    }

    return jsonify(response)

def get_location_for_call(room_number):
    try:
        location_db_obj = Location.objects(room_number=room_number).order_by('-updated_at').first()
        if location_db_obj is not None:
            return get_location_display(location_db_obj)
        return ''
    except Exception as e:
        stacktrace = traceback.format_exc()
        log.error("exception in get_location_for_call for room %r, e %r", room_number, str(e))
        log.error("%r", stacktrace)
        return ""
'''
Note - for now we ignore the psap_id
returns recent call history
'''
@calls.route('/recent', methods=['GET'])
def recent():
    log.info("get recent calls")
    log.info("get current calls")
    calls = []
    # todo - add limit of 1 month to this data
    for conference_db_obj in Conference.objects(status__in=['closed', 'abandoned']):
        conference_json = get_json_from_db_obj(conference_db_obj, ignore_fields=ignore_conference_fields)

        conference_json['location'] = get_location_for_call(conference_db_obj.room_number)
        conference_json['participants'] = get_conference_participants_json(conference_db_obj.room_number)
        conference_json['event_log'] = get_conference_event_log_json(conference_db_obj.room_number)
        calls.append(conference_json)

    response = {
        'success' : True,
        'calls' : calls
    }

    return jsonify(response)

'''
Get conference room for call id
'''
@calls.route('/get_room', methods=['GET'])
def get_room():
    try:
        call_id = get_argument('call_id')
        call_obj = Call.objects.get(sip_call_id=call_id)
        response = {
            'success': True,
            'room_number' : call_obj.room_number
        }
        return jsonify(response)
    except:
        response = {
            'success': False
        }
        return jsonify(response)


def get_conference_participants_json(room_number):
    participants = []
    for participant_db_obj in ConferenceParticipant.objects(room_number=room_number):
        participant_json = get_json_from_db_obj(participant_db_obj)
        participants.append(participant_json)
    return participants

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

@calls.route('/conference/<room_number>', methods=['GET'])
def conference_info(room_number):
    conference_db_obj = Conference.objects.get(room_number=room_number)
    conference_json = get_json_from_db_obj(conference_db_obj, ignore_fields=ignore_conference_fields)
    conference_json['duration'] = get_conference_duration(conference_db_obj)
    conference_json['participants'] = get_conference_participants_json(room_number)
    conference_json['event_log'] = get_conference_event_log_json(room_number)

    response = {
        'success' : True,
        'conference_data' : conference_json
    }

    return jsonify(response)

@calls.route('/conference/participants/<room_number>', methods=['GET'])
def conference_participants(room_number):
    participants_json = get_conference_participants_json(room_number)

    response = {
        'success' : True,
        'participants' : participants_json
    }

    return jsonify(response)

'''
Update the conference participant values like send_video, mute, send_audio, send_text 
'''
@calls.route('/conference/participants/<room_number>', methods=['PUT', 'POST'])
def conference_participants_update(room_number):
    try:
        sip_uri = get_argument('sip_uri')
        if (sip_uri is None) or (sip_uri == ''):
            raise ValueError('missing sip_uri')
        participant_db_obj = ConferenceParticipant.objects(room_number=room_number, sip_uri=sip_uri)
        set_db_obj_from_request(log, participant_db_obj, request)
        participant_db_obj.save()

        data = NotificationData(room_number=room_number)
        copy_request_data_to_object(request, data)
        NotificationCenter().post_notification('ConferenceParticipantDBUpdated', '', data)

        return jsonify({
            'success' : True
        })
    except Exception as e:
        stacktrace = traceback.print_exc()
        log.error("%r", stacktrace)
        log.error("conference_participants_update error %r", e)

        return jsonify ({
            'success' : False,
            'reason' : str(e)
        })


@calls.route('/conference/event_log/<room_number>', methods=['GET'])
def conference_event_log(room_number):
    event_log_json = get_conference_event_log_json(room_number)

    response = {
        'success' : True,
        'event_log' : event_log_json
    }

    return jsonify(response)


@calls.route('/join/<room_number>', methods=['GET'])
def join_conference(room_number):
    pass


@calls.route('/dial/<phone_number>', methods=['GET'])
def dial_number(phone_number):
    pass

@calls.route('/update/<room_number>', methods=['PUT', 'POST'])
def update_call(room_number):
    try:
        if (room_number is None) or (room_number == ''):
            raise ValueError('missing or invalid room_number')

        conf_db_obj = Conference.objects.get(room_number=room_number)

        set_db_obj_from_request(conf_db_obj, request)
        conf_db_obj.save()
        response = {'success':True}
        return jsonify(response)
    except Exception as e:
        stactrace = traceback.format_exc()
        log.error("exception %r in update_call for room %r", e, room_number)
        log.error("%r",stactrace)
        response = {
            'success' : False,
            'reason' : str(e)
        }

        return jsonify(response)


@calls.route('/recordings/<path:path>')
def send_recording(path):
    log.info("send_recording for %r", path)
    return send_from_directory('recordings', path)


'''
sample current calls
calls = [
    {
        'conf_id' : '1123',
        'call_type' : 'sos',
        'media' : ['voice'],
        'ani' : '4153054541',
        'name' : 'tarun',
        'location' : '665 pine str, san francisco, california',
        'note' : 'his pet is not feeling well',
        'date_time' : '9:15 am, Mar 12',
        'status' : 'ringing'
    },
    {
        'conf_id': '1124',
        'call_type': 'sos',
        'media': ['voice'],
        'ani': '4153054541',
        'name': 'mike',
        'location': '665 pine str, san francisco, california',
        'note': '',
        'date_time': '9:00 am, Mar 12',
        'status': 'active'
    },
    {
        'conf_id': '1125',
        'call_type': 'sos',
        'media': ['voice'],
        'ani': '6503054542',
        'name': 'nate',
        'location': '665 pine str, san mateo, california',
        'note': 'saw robbery',
        'date_time': '8:45 am, Mar 12',
        'status': 'active'
    },
    {
        'conf_id': '1126',
        'call_type': 'sos',
        'media': ['voice'],
        'ani': '4153054541',
        'name': 'tarun',
        'location': '665 pine str, san francisco, california',
        'note': '',
        'date_time': '8:00 am, Mar 12',
        'status': 'abandoned'
    },
    {
        'conf_id': '1127',
        'call_type': 'sos',
        'media': ['voice'],
        'ani': '4153054541',
        'name': 'matt',
        'location': '665 pine str, santa clara, california',
        'note': '',
        'date_time': '7:30 am, Mar 12',
        'status': 'abandoned'
    },
    {
        'conf_id': '1128',
        'call_type': 'sos',
        'media': ['text'],
        'ani': '415551212',
        'name': 'tom sawyer',
        'location': '665 pine str, san jose, california',
        'note': '',
        'date_time': '7:15 am, Mar 12',
        'status': 'abandone'
    }
]

sample recent calls
calls = [
    {
        'conf_id' : '2123',
        'call_type' : 'sos',
        'media' : ['voice'],
        'ani' : '4153054541',
        'name' : 'tom sawyer',
        'location' : '665 pine str, san francisco, california',
        'note' : 'prank call',
        'date_time' : '9:15 am, Mar 12',
        'status' : 'closed'
    },
    {
        'conf_id': '2124',
        'call_type': 'sos',
        'media': ['voice'],
        'ani': '4153054541',
        'name': 'tarun',
        'location': '665 pine str, san francisco, california',
        'note': 'son not well',
        'date_time': '9:00 am, Mar 12',
        'status': 'callback'
    },
    {
        'conf_id': '1125',
        'call_type': 'sos',
        'media': ['voice'],
        'ani': '6503054542',
        'name': 'michael jordon',
        'location': '665 pine str, san jose, california',
        'note': 'fire in apartment',
        'date_time': '8:45 am, Mar 12',
        'status': 'closed'
    },
    {
        'conf_id': '1126',
        'call_type': 'sos',
        'media': ['voice'],
        'ani': '4153054541',
        'name': 'steph curry',
        'location': '665 pine str, monterey, california',
        'note': '',
        'date_time': '8:00 am, Mar 12',
        'status': 'abandoned'
    },
    {
        'conf_id': '1127',
        'call_type': 'sos',
        'media': ['voice'],
        'ani': '4153054541',
        'name': 'nate',
        'location': '665 pine str, san francisco, california',
        'note': 'his pet is not feeling well',
        'date_time': '7:30 am, Mar 12',
        'status': 'abandoned'
    },
    {
        'conf_id': '1128',
        'call_type': 'sos',
        'media': ['text'],
        'ani': '415551212',
        'name': 'tarun',
        'location': '665 pine str, mountain view, california',
        'note': 'his pet is not feeling well',
        'date_time': '7:15 am, Mar 12',
        'status': 'closed'
    }
]
'''
