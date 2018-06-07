import traceback
import os.path
import arrow
from flask import Blueprint, jsonify, request, send_from_directory
from flask_cors import CORS
from sylk.configuration import ServerConfig
from sylk.applications import ApplicationLogger
from sylk.applications.psap import PSAPApplication
from sylk.db.schema import Conference, ConferenceParticipant, Call, Location
from application.notification import NotificationCenter, NotificationData
from sylk.utils import get_json_from_db_obj, set_db_obj_from_request, copy_request_data_to_object
from utils import get_argument
from bson.objectid import ObjectId
from mongoengine import Q
from sylk.db.calls import get_conference_participants_json, get_active_calltakers, get_conference_event_log_json, \
                            get_conference_duration, get_conference_json, get_location_for_call

calls = Blueprint('calls', __name__,
                        template_folder='templates')

CORS(calls)
log = ApplicationLogger(__package__)


'''
Note - for now we ignore the psap_id
returns currently active calls
'''

@calls.route('/', methods=['GET'])
def current():
    log.info("get current calls")
    calls = []
    for conference_db_obj in Conference.objects(Q(status__in=['init', 'ringing', 'ringing_queued', 'queued', 'active']) | (Q(status='abandoned') & Q(callback=False))):
        conference_json = get_conference_json(conference_db_obj)
        calls.append(conference_json)
    response = {
        'success' : True,
        'calls' : calls
    }

    return jsonify(response)

'''
Note - for now we ignore the psap_id
returns recent call history
'''
@calls.route('/recent', methods=['GET'])
def recent():
    log.info("get recent calls")
    calls = []
    # todo - add limit of 1 month to this data
    for conference_db_obj in Conference.objects(status__in=['closed', 'abandoned']):
        conference_json = get_conference_json(conference_db_obj)
        calls.append(conference_json)

    response = {
        'success' : True,
        'calls' : calls
    }

    return jsonify(response)


'''
Note - for now we ignore the psap_id
returns recent call history
'''
@calls.route('/lastMonth', methods=['GET'])
def lastMonth():
    log.info("get current calls")
    calls = []
    arr_cur_time = arrow.utcnow()
    arr_last_month = arr_cur_time.shift(days=-30)

    for conference_db_obj in Conference.objects(start_time__gt=arr_last_month.naive):
        conference_json = get_conference_json(conference_db_obj)
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

'''
Old code
        filters = {'psap' : cls.psapName, 'end' : {'$ne' : None}}
        if (len(callingNumber) > 0) :
            filters['caller.contact'] = { '$regex' : callingNumber , '$options' : 'i'} 
        if (len(callingLocation) > 0) :
            locationRegEx = "/%s/i" % callingLocation
            filters['$or'] = [{'locations.name' : locationRegEx}, {'locations.community' : locationRegEx}, {'locations.state' : locationRegEx}, {'locations.location' : locationRegEx} ]
        if (len(notes) > 0) :
            locationRegEx = "/%s/i" % callingLocation
            filters['notes'] = { '$regex' : notes , '$options' : 'i'} 
        if (len(startDate) > 0) and (len(endDate) > 0) :
            logger.debug("startDate is %r", startDate)
            logger.debug("endDate is %r", endDate)
            locationRegEx = "/%s/i" % callingLocation
            filters['start'] = {'$gte' : convertASDateToDatetime(startDate),
                                '$lt': convertASDateToDatetime(endDate) } 
        logger.debug("filters are %r", filters)
        fullCallRecords = collection.find(filters)
        fullCallsData = [bindable.Object(callRecord) \
                for callRecord in fullCallRecords]
        for callData in fullCallsData:
            # logger.debug('callData is %r' % callData)
            del callData['_id']
            callData['start'] = cls.formatISODate(callData['start'])
            callData['end'] = cls.formatISODate(callData['end'])


'''

@calls.route('/search', methods=['GET'])
def search_calls():
    try:
        log.info('inside search for psap %s', ServerConfig.psap_id)
        calling_number = get_argument('calling_number')
        location = get_argument('location')
        note = get_argument('note')
        start_time = get_argument('start_time')
        end_time = get_argument('end_time')

        filters = {'psap_id' : ObjectId(ServerConfig.psap_id), 'status' : {'$nin' : ['active', 'init', 'ringing', 'on_hold', 'queued', 'ringing_queued']}}
        if (calling_number != None) and (len(calling_number) > 0) :
            log.info('inside search calling_number %s', calling_number)
            filters['caller_ani'] = { '$regex' : calling_number , '$options' : 'i'}
        if (location != None) and (len(location) > 0) :
            log.info('inside search location %s', location)
            filters['location_display'] = { '$regex' : location, '$options' : 'i'}
        if (note != None) and (len(note) > 0) :
            log.info('inside search note %s', note)
            note_reg_ex = "/%s/i" % note
            filters['note'] = { '$regex' : note_reg_ex, '$options' : 'i'}
        if (start_time != None) and (end_time != None) and (len(start_time) > 0) and (len(end_time) > 0) :
            log.info("start_time is %r", start_time)
            log.info("end_time is %r", end_time)
            arrow_start = arrow.get(start_time)
            arrow_end = arrow.get(end_time)
            complex_time_format = 'YYYY,MM,DD,HH,mm,ss,SSSSSS'
            formatted_start_time = arrow_start.format(complex_time_format)
            formatted_end_time = arrow_end.format(complex_time_format)
            filters['start_time'] = {'$gte' : formatted_start_time,
                                '$lt': formatted_end_time }
        log.info("inside call search filters is %r", filters)
        calls_cursor = Conference.objects(__raw__=filters)
        log.info('calls search found %d records', len(calls_cursor))
        calls = []
        for call_db_obj in calls_cursor:
            # should return date, call, type, caller, callback, location, long, lat, notes, status
            call_data = get_json_from_db_obj(call_db_obj, ignore_fields=['psap_id', 'user_id'])
            calls.append(call_data)

        response = {'success': True, 'calls' : calls}

        return jsonify(response)
    except Exception as e:
        stacktrace = traceback.format_exc()
        log.error('exception in search %s', str(e))
        log.error("%s", stacktrace)
        response = {
            'success': False,
            'error' : str(e)
        }
        return jsonify(response)


@calls.route('/conference/debug_info/<room_number>', methods=['GET'])
def conference_debug_info(room_number):
    psap_app = PSAPApplication()
    debug_info = psap_app.get_room_debug_info(room_number)
    return jsonify(debug_info)


@calls.route('/conference/<room_number>', methods=['GET'])
def conference_info(room_number):
    conference_db_obj = Conference.objects.get(room_number=room_number)

    response = {
        'success' : True,
        'conference_data' : get_conference_json(conference_db_obj),
        'participants': get_conference_participants_json(room_number),
        'event_log' : get_conference_event_log_json(room_number)
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


@calls.route('/conference/hold/<room_number>', methods=['PUT', 'POST'])
def conference_put_on_hold(room_number):
    try:
        calltaker = get_argument('calltaker')
        if (calltaker is None) or (calltaker == ''):
            raise ValueError('missing calltaker')

        psap_app = PSAPApplication()
        psap_app.put_calltaker_on_hold(room_number, calltaker)

        return jsonify({
            'success' : True
        })
    except Exception as e:
        stacktrace = traceback.print_exc()
        log.error("%r", stacktrace)
        log.error("conference put hold error %r", e)

        return jsonify ({
            'success' : False,
            'reason' : str(e)
        })

@calls.route('/conference/unhold/<room_number>', methods=['PUT', 'POST'])
def conference_release_on_hold(room_number):
    try:
        calltaker = get_argument('calltaker')
        if (calltaker is None) or (calltaker == ''):
            raise ValueError('missing calltaker')
        psap_app = PSAPApplication()
        psap_app.remove_calltaker_on_hold(room_number, calltaker)

        return jsonify({
            'success' : True
        })
    except Exception as e:
        stacktrace = traceback.print_exc()
        log.error("%r", stacktrace)
        log.error("conference release hold error %r", e)

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
    if os.path.isfile(path):
        return send_from_directory('recordings', path)
    else:
        return send_from_directory('recordings', 'ca4182ebac4ed29dc2f8d9209fccca.wav')


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
