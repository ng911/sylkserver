import traceback
import os.path
import arrow
import uuid
import requests
import subprocess
import shutil
import logging

from flask import current_app, Blueprint, jsonify, request, send_file, abort, render_template
from flask_cors import CORS
from bson.objectid import ObjectId
from mongoengine import Q

from ..db.schema import Conference, Call
from ..utils import get_json_from_db_obj, set_db_obj_from_request
from .utils import get_argument
from ..db.calls import get_conference_json, clear_abandoned_calls
from .decorators import check_exceptions

calls = Blueprint('calls', __name__,
                        template_folder='templates')

CORS(calls)

log = logging.getLogger("emergent-ng911")


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

    for conference_db_obj in Conference.objects(start_time__gt=arr_last_month.naive).order_by('-start_time')[0:150]:
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

@calls.route('/print/<room_number>', methods=['GET'])
def get_print_data(room_number):
    conf_obj = Conference.objects.get(room_number=room_number)
    return render_template('call_print.html', conference=conf_obj)


@calls.route('/search', methods=['GET'])
def search_calls():
    try:
        psap_id = get_argument('psap_id')
        log.info('inside search for psap %s', psap_id)
        calling_number = get_argument('calling_number')
        location = get_argument('location')
        note = get_argument('note')
        start_time = get_argument('start_time')
        end_time = get_argument('end_time')
        per_page = get_argument('per_page')
        if per_page is not None:
            per_page = int(per_page)
        page_no = get_argument('page')
        if page_no is not None:
            page_no = int(page_no)

        filters = {'psap_id' : ObjectId(psap_id), 'status' : {'$nin' : ['active', 'init', 'ringing', 'on_hold', 'queued', 'ringing_queued']}}
        if (calling_number != None) and (len(calling_number) > 0) :
            log.info('inside search calling_number %s', calling_number)
            filters['caller_ani'] = { '$regex' : calling_number , '$options' : 'i'}
        if (location != None) and (len(location) > 0) :
            log.info('inside search location %s', location)
            filters['location_display'] = { '$regex' : location, '$options' : 'i'}
        if (note != None) and (len(note) > 0) :
            log.info('inside search note %s', note)
            filters['note'] = { '$regex' : note, '$options' : 'i'}
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
        calls_cursor = Conference.objects(__raw__=filters).order_by('-start_time')
        count = len(calls_cursor)
        if (per_page is not None) and (per_page > 0) and (page_no is not None):
            log.info('inside search note per_page %d, page_no %d', per_page, page_no)
            start_index = (page_no - 1) * per_page
            end_index = start_index + per_page
            log.info('inside search note start_index %d, end_index %d', start_index, end_index)
            calls_cursor = Conference.objects(__raw__=filters).order_by('-start_time')[start_index:end_index]

        log.info('calls search found %d records', len(calls_cursor))
        calls = []
        for call_db_obj in calls_cursor:
            # should return date, call, type, caller, callback, location, long, lat, notes, status
            call_data = get_json_from_db_obj(call_db_obj, ignore_fields=['psap_id', 'user_id'])
            calls.append(call_data)

        response = {'success': True, 'calls' : calls, 'total_records' : count}

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

@calls.route('/abandoned/clear/<psap_id>', methods=['GET', 'PUT', 'POST'])
@check_exceptions
def api_clear_abandoned_calls(psap_id):
    try:
        log.info("inside api_clear_abandoned_calls")
        callback_number = get_argument('callback_number')
        caller_ani = get_argument('caller_ani')
        calls_cleared = clear_abandoned_calls(psap_id, callback_number=callback_number, caller_ani=caller_ani)
        response = {'success': True, 'calls_cleared' : calls_cleared}
        return jsonify(response)
    except Exception as e:
        stacktrace = traceback.format_exc()
        log.error('exception in api_clear_abandoned_calls %s', str(e))
        log.error("%s", stacktrace)
        response = {
            'success': False,
            'error' : str(e)
        }
        return jsonify(response)


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
        stacktrace = traceback.format_exc()
        log.error("exception %s in update_call for room %r", str(e), room_number)
        log.error("%s",stacktrace)
        response = {
            'success' : False,
            'reason' : str(e)
        }

        return jsonify(response)


@calls.route('/recordings/<path:path>')
def send_recording(path):
    log.info("send_recording for %s, app.root_path %s", path, current_app.root_path)
    recording_dir = os.path.join(current_app.root_path, '../../recordings')
    recording_dir = os.path.abspath(recording_dir)
    full_path = os.path.join(recording_dir, path)
    log.info('recording_file path is %s', full_path)
    try:
        # todo remove this later
        if os.path.isfile(full_path):
            return send_file(full_path)
        else:
            abort(404)
    except Exception as e:
        stacktrace = traceback.format_exc()
        log.error("send_recording for file %s, error %s", path, str(e))
        log.error("%s", stacktrace)
        abort(503)

@calls.route('/media/<path:path>')
def send_media(path):
    log.info("send_media for %s, app.root_path %s", path, current_app.root_path)
    recording_dir = os.path.join(current_app.root_path, '../../media')
    recording_dir = os.path.abspath(recording_dir)
    full_path = os.path.join(recording_dir, path)
    log.info('media path is %s', full_path)
    try:
        # todo remove this later
        if os.path.isfile(full_path):
            return send_file(full_path)
        else:
            abort(404)
    except Exception as e:
        stacktrace = traceback.format_exc()
        log.error("send_media for file %s, error %s", path, str(e))
        log.error("%s", stacktrace)
        abort(503)

@calls.route('/convert3gpp/to/mp4', methods=['GET', 'POST'])
def convertFileTo3gpp():
    media_url = get_argument("media_url")

    file_name = "%s" % str(uuid.uuid4())
    file_name_3gpp = "%s.3gpp" % file_name
    file_name_mp4 = "%s.mp4" % file_name
    resp = requests.get(media_url, stream=True)

    media_dir = os.path.join(current_app.root_path, '../../media')
    media_dir = os.path.abspath(media_dir)
    file_path_3gpp = os.path.join(media_dir, file_name_3gpp)
    file_path_mp4 = os.path.join(media_dir, file_name_mp4)

    error = True
    with open(file_path_3gpp, 'wb') as f:
        shutil.copyfileobj(resp.raw, f)
        out = subprocess.call(["ffmpeg", "-i", file_path_3gpp, file_path_mp4])
        if out == 0:
            error = False
    if not error:
        response = {
            "success" : True,
            "media_url" : "calls/media/%s" % file_name_mp4
        }
    else:
        response = {
            "success" : False
        }
    return jsonify(response)

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
