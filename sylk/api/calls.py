import traceback
import os.path
import arrow
from flask import current_app, Blueprint, jsonify, request, send_file, abort, render_template
from flask_cors import CORS
from sylk.configuration import ServerConfig
from sylk.applications import ApplicationLogger
import sylk.applications.psap as psap
from sylk.db.schema import Conference, ConferenceParticipant, Call, CallTransferLine, IncomingLink, ConferenceMessage
from application.notification import NotificationCenter, NotificationData
from sylk.utils import get_json_from_db_obj, set_db_obj_from_request, copy_request_data_to_object
from utils import get_argument
from bson.objectid import ObjectId
from mongoengine import Q
import sylk.db.calls as db_calls

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
        conference_json = db_calls.get_conference_json(conference_db_obj)
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
        conference_json = db_calls.get_conference_json(conference_db_obj)
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
        conference_json = db_calls.get_conference_json(conference_db_obj)
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
        log.info('inside search for psap %s', ServerConfig.psap_id)
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

        filters = {'psap_id' : ObjectId(ServerConfig.psap_id), 'status' : {'$nin' : ['active', 'init', 'ringing', 'on_hold', 'queued', 'ringing_queued']}}
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

@calls.route('/abandoned/clear', methods=['GET', 'PUT', 'POST'])
def clear_abandoned_calls():
    try:
        callback_number = get_argument('callback_number')
        caller_ani = get_argument('caller_ani')
        calls_cleared = db_calls.clear_abandoned_calls(callback_number=callback_number, caller_ani=caller_ani)
        response = {'success': True, 'calls_cleared' : calls_cleared}
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
    psap_app = psap.PSAPApplication()
    debug_info = psap_app.get_room_debug_info(room_number)
    return jsonify(debug_info)


@calls.route('/conference/<room_number>', methods=['GET'])
def conference_info(room_number):
    conference_db_obj = Conference.objects.get(room_number=room_number)

    response = {
        'success' : True,
        'conference_data' : db_calls.get_conference_json(conference_db_obj),
        'participants': db_calls.get_conference_participants_json(room_number),
        'event_log' : db_calls.get_conference_event_log_json(room_number)
    }

    return jsonify(response)


@calls.route('/conference/participants/<room_number>', methods=['GET'])
def conference_participants(room_number):
    participants_json = db_calls.get_conference_participants_json(room_number)

    response = {
        'success' : True,
        'participants' : participants_json
    }

    return jsonify(response)

@calls.route('/conference/participant/mute/<room_number>', methods=['PUT', 'POST'])
def conference_participant_mute(room_number):
    try:
        sip_uri = get_argument('sip_uri')
        muted = get_argument('mute')
        log.info('conference_participant_mute sip_uri %r, muted %r')
        '''
        if (sip_uri is None) or (sip_uri == ''):
            raise ValueError('missing sip_uri')
        participant_db_obj = ConferenceParticipant.objects.get(room_number=room_number, sip_uri=sip_uri)
        participant_db_obj.mute = muted
        #set_db_obj_from_request(participant_db_obj, request)
        participant_db_obj.save()

        data = NotificationData(room_number=room_number, sip_uri=sip_uri, mute=muted)
        NotificationCenter().post_notification('ConferenceParticipantDBUpdated', '', data)
        '''
        psap_application = psap.PSAPApplication()
        psap_application.mute_user(room_number, sip_uri, muted)
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


'''
Update the conference participant values like send_video, mute, send_audio, send_text 
'''
@calls.route('/conference/participants/<room_number>', methods=['PUT', 'POST'])
def conference_participants_update(room_number):
    try:
        sip_uri = get_argument('sip_uri')
        if (sip_uri is None) or (sip_uri == ''):
            raise ValueError('missing sip_uri')
        participant_db_obj = ConferenceParticipant.objects.get(room_number=room_number, sip_uri=sip_uri)

        #set_db_obj_from_request(participant_db_obj, request)
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

@calls.route('/conference/mute_calltaker/<room_number>', methods=['PUT', 'POST'])
def conference_mute_calltaker(room_number):
    try:
        name = get_argument('name')
        if (name is None) or (name == ''):
            raise ValueError('missing name')
        muted = get_argument('muted')
        if (muted is None) or (muted == ''):
            raise ValueError('missing muted')
        psap_application = psap.PSAPApplication()
        psap_application.mute_calltaker(room_number, name, muted)

        '''
        participant_db_obj = ConferenceParticipant.objects(room_number=room_number, sip_uri=sip_uri)
        set_db_obj_from_request(log, participant_db_obj, request)
        participant_db_obj.save()

        data = NotificationData(room_number=room_number)
        copy_request_data_to_object(request, data)
        NotificationCenter().post_notification('ConferenceParticipantDBUpdated', '', data)
        '''
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


@calls.route('/conference/mute_all/<room_number>', methods=['PUT', 'POST'])
def conference_mute_all(room_number):
    try:
        psap_application = psap.PSAPApplication()
        muted = get_argument('muted')
        if (muted is None) or (muted == ''):
            raise ValueError('missing muted')
        psap_application.mute_all(room_number, muted)
        '''
        participant_db_obj = ConferenceParticipant.objects(room_number=room_number, sip_uri=sip_uri)
        set_db_obj_from_request(log, participant_db_obj, request)
        participant_db_obj.save()

        data = NotificationData(room_number=room_number)
        copy_request_data_to_object(request, data)
        NotificationCenter().post_notification('ConferenceParticipantDBUpdated', '', data)
        '''
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

        psap_app = psap.PSAPApplication()
        psap_app.put_calltaker_on_hold(room_number, calltaker)

        return jsonify({
            'success' : True
        })
    except Exception as e:
        stacktrace = traceback.print_exc()
        log.error("conference put hold error %s", str(e))
        log.error("%r", stacktrace)

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
        psap_app = psap.PSAPApplication()
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

@calls.route('/conference/tty/enable/<room_number>', methods=['PUT', 'POST'])
def conference_tty_enable(room_number):
    try:
        psap_app = psap.PSAPApplication()
        psap_app.enable_tty(room_number)

        return jsonify({
            'success' : True
        })
    except Exception as e:
        stacktrace = traceback.print_exc()
        log.error("%r", stacktrace)
        log.error("conference_tty_enable error %r", e)

        return jsonify ({
            'success' : False,
            'reason' : str(e)
        })

@calls.route('/conference/tty/send/<room_number>', methods=['PUT', 'POST'])
def conference_tty_send(room_number):
    try:
        ttyData = get_argument('data')
        if (ttyData is None) or (ttyData == ''):
            raise ValueError('missing tty data to send')
        psap_app = psap.PSAPApplication()
        tty_text = psap_app.send_tty(room_number, ttyData)

        return jsonify({
            'success' : True,
            'tty_text' : tty_text
        })
    except Exception as e:
        stacktrace = traceback.print_exc()
        log.error("%r", stacktrace)
        log.error("conference_tty_send error %r", e)

        return jsonify ({
            'success' : False,
            'reason' : str(e)
        })

@calls.route('/conference/tty/get/<room_number>', methods=['GET'])
def conference_tty_get(room_number):
    try:
        conf_db_obj = Conference.objects.get(room_number=room_number)
        if (hasattr(conf_db_obj, 'tty_text')):
            tty_text = conf_db_obj.tty_text
        else:
            tty_text = ''

        return jsonify({
            'success' : True,
            'tty_text' : tty_text
        })
    except Exception as e:
        stacktrace = traceback.print_exc()
        log.error("%r", stacktrace)
        log.error("conference_tty_get error %r", e)

        return jsonify ({
            'success' : False,
            'reason' : str(e)
        })


@calls.route('/conference/msrp/text/<room_number>', methods=['GET'])
def conference_msrp_text(room_number):
    try:
        log.debug("/conference/msrp/text for room %s", room_number)
        messages = []
        for db_obj in ConferenceMessage.objects(room_number=room_number):
            # should return date, call, type, caller, callback, location, long, lat, notes, status
            message_data = get_json_from_db_obj(db_obj)
            messages.append(message_data)

        return jsonify ({
            'success': True,
            'messages' : messages,
            'room_number' : room_number
        })
    except Exception as e:
        stacktrace = traceback.print_exc()
        log.error("%r", stacktrace)
        log.error("conference_msrp_text error %r", e)

        return jsonify ({
            'success' : False,
            'reason' : str(e)
        })

@calls.route('/conference/msrp/send/<room_number>', methods=['PUT', 'POST'])
def conference_msrp_send(room_number):
    try:
        text = get_argument('text')
        sender = get_argument('sender')
        if (text is None) or (text == ''):
            raise ValueError('missing text to send')
        if (sender is None) or (sender == ''):
            raise ValueError('missing sender')
        psap_app = psap.PSAPApplication()
        message_id = psap_app.send_msrp_text(room_number, sender, text)

        return jsonify({
            'success' : True,
            'message_id' : message_id
        })
    except Exception as e:
        stacktrace = traceback.print_exc()
        log.error("%r", stacktrace)
        log.error("conference_tty_send error %r", e)

        return jsonify ({
            'success' : False,
            'reason' : str(e)
        })


@calls.route('/conference/event_log/<room_number>', methods=['GET'])
def conference_event_log(room_number):
    event_log_json = db_calls.get_conference_event_log_json(room_number)

    response = {
        'success' : True,
        'event_log' : event_log_json
    }

    return jsonify(response)


@calls.route('/conference/transfer_lines/<room_number>', methods=['GET'])
def get_call_transfer_lines(room_number):
    try:
        log.info('inside get_call_transfer_lines for room %s', room_number)
        conf_db_obj = Conference.objects.get(room_number=room_number)
        log.info('inside get_call_transfer_lines for room %s, status %r, call_type %r', room_number, conf_db_obj.status, conf_db_obj.call_type)
        transfer_lines = []
        if (conf_db_obj.status == 'active') and (conf_db_obj.call_type == 'sos'):
            log.info('conf is active and sos type')
            log.info('conf link_id is %r', conf_db_obj.link_id)
            if hasattr(conf_db_obj, 'link_id') and (conf_db_obj.link_id != None) and (conf_db_obj.link_id != ''):
                link_obj = IncomingLink.objects.get(link_id=conf_db_obj.link_id)
                type = None
                log.info('link_obj.orig_type is %s', link_obj.orig_type)
                if link_obj.orig_type == 'sos_wireless':
                    type = 'wireless'
                elif link_obj.orig_type == 'sos_wireline':
                    type = 'wireline'
                if type is not None:
                    for call_transfer_line in CallTransferLine.objects(psap_id=ServerConfig.psap_id, type=type):
                        transfer_lines.append({'name' : call_transfer_line.name, 'star_code' : call_transfer_line.star_code})

        response = {
            'success' : True,
            'transfer_lines': transfer_lines
        }

        return jsonify(response)
    except Exception as e:
        stacktrace = traceback.format_exc()
        log.error("exception %s in conference_transfer_lines for room %r", str(e), room_number)
        log.error("%s", stacktrace)
        response = {
            'success': False,
            'reason': str(e)
        }
        return jsonify(response)


@calls.route('/invite/<room_number>/<phone_number>', methods=['GET'])
def invite_to_conference(room_number, phone_number):
    try:
        psap_application = psap.PSAPApplication()
        call_from = get_argument('from')

        ref_id = psap_application.invite_to_conference(room_number, call_from, phone_number)

        response = {'success': True, 'ref_id' : ref_id}
        return jsonify(response)
    except Exception as e:
        stacktrace = traceback.format_exc()
        log.error("exception %s in invite_to_conference for room %r", str(e), room_number)
        log.error("%s", stacktrace)
        response = {
            'success': False,
            'reason': str(e)
        }
        return jsonify(response)

@calls.route('/cancel_invite/<room_number>/<call_id>', methods=['GET'])
def cancel_invite_to_conference(room_number, call_id):
    try:
        psap_application = psap.PSAPApplication()
        call_from = get_argument('from')
        log.info('inside cancel_invite_to_conference for room {}, call id {}, from {}'.format(room_number, call_id, call_from))
        psap_application.cancel_invite_to_conference(room_number, call_from, call_id)

        response = {'success': True}
        return jsonify(response)
    except Exception as e:
        stacktrace = traceback.format_exc()
        log.error("exception %s in invite_to_conference for room %r", str(e), room_number)
        log.error("%s", stacktrace)
        response = {
            'success': False,
            'reason': str(e)
        }
        return jsonify(response)

@calls.route('/conference/send_dtmf/<room_number>', methods=['GET', 'PUT', 'POST'])
def send_dtmf(room_number):
    try:
        dtmf = get_argument('dtmf')
        psap_application = psap.PSAPApplication()
        psap_application.send_dtmf(room_number, dtmf)

        response = {'success': True}
        return jsonify(response)
    except Exception as e:
        stacktrace = traceback.format_exc()
        log.error("exception %s in send_dtmf for room %r", str(e), room_number)
        log.error("%s", stacktrace)
        response = {
            'success': False,
            'reason': str(e)
        }
        return jsonify(response)


@calls.route('/conference/transfer_line/<room_number>', methods=['GET', 'PUT', 'POST'])
def transfer_line(room_number):
    try:
        star_code = get_argument('star_code')
        psap_application = psap.PSAPApplication()
        psap_application.star_code_transfer(room_number, star_code)

        response = {'success': True}
        return jsonify(response)
    except Exception as e:
        stacktrace = traceback.format_exc()
        log.error("exception %s in transfer_line for room %r", str(e), room_number)
        log.error("%s", stacktrace)
        response = {
            'success': False,
            'reason': str(e)
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
