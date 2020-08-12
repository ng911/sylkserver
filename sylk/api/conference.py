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
#from sylk.configuration import ServerConfig
#from sylk.applications import ApplicationLogger
from ..applications.psap import PSAPApplication
from sylk.db.schema import Conference, ConferenceParticipant, Call, CallTransferLine, IncomingLink, ConferenceMessage
from application.notification import NotificationCenter, NotificationData
from ..utils import get_json_from_db_obj, set_db_obj_from_request, copy_request_data_to_object
from .utils import get_argument
from bson.objectid import ObjectId
from mongoengine import Q
from ..db.calls import get_conference_json, get_conference_participants_json, get_conference_event_log_json
from .decorators import check_exceptions

conference = Blueprint('conference', __name__,
                        template_folder='templates')

CORS(conference)
#log = ApplicationLogger(__package__)

log = logging.getLogger("emergent-ng911")


@conference.route('/debug_info/<room_number>', methods=['GET'])
def conference_debug_info(room_number):
    psap_app = PSAPApplication()
    debug_info = psap_app.get_room_debug_info(room_number)
    return jsonify(debug_info)


@conference.route('/testme/', methods=['GET'])
def conference_test():
    response = {
        'success' : True
    }

    return jsonify(response)


@conference.route('/<room_number>', methods=['GET'])
def conference_info(room_number):
    conference_db_obj = Conference.objects.get(room_number=room_number)

    response = {
        'success' : True,
        'conference_data' : get_conference_json(conference_db_obj),
        'participants': get_conference_participants_json(room_number),
        'event_log' : get_conference_event_log_json(room_number)
    }

    return jsonify(response)

@conference.route('/transfer/caller/<room_number>', methods=['GET', 'POST'])
@check_exceptions
def conference_transfer_caller(room_number):
    #transfer_to = get_argument("transfer_to", "sip:sos@sos-fire_psap.psapcloud.com")
    log.info("inside conference_transfer_caller")
    target = get_argument("target", None)
    log.info("inside conference_transfer_caller to target %r", target)
    if target != None:
        psap_application = PSAPApplication()
        psap_application.transfer_caller(room_number, target)

@conference.route('/participants/<room_number>', methods=['GET'])
def conference_participants(room_number):
    participants_json = get_conference_participants_json(room_number)

    response = {
        'success' : True,
        'participants' : participants_json
    }

    return jsonify(response)

@conference.route('/participant/mute/<room_number>', methods=['PUT', 'POST'])
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
        psap_application = PSAPApplication()
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
@conference.route('/participants/<room_number>', methods=['PUT', 'POST'])
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

@conference.route('/mute_calltaker/<room_number>', methods=['PUT', 'POST'])
def conference_mute_calltaker(room_number):
    try:
        name = get_argument('name')
        if (name is None) or (name == ''):
            raise ValueError('missing name')
        muted = get_argument('muted')
        if (muted is None) or (muted == ''):
            raise ValueError('missing muted')
        psap_application = PSAPApplication()
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


@conference.route('/mute_all/<room_number>', methods=['PUT', 'POST'])
def conference_mute_all(room_number):
    try:
        psap_application = PSAPApplication()
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

@conference.route('/hold/<room_number>', methods=['PUT', 'POST'])
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
        log.error("conference put hold error %s", str(e))
        log.error("%r", stacktrace)

        return jsonify ({
            'success' : False,
            'reason' : str(e)
        })

@conference.route('/unhold/<room_number>', methods=['PUT', 'POST'])
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

@conference.route('/tty/enable/<room_number>', methods=['PUT', 'POST'])
def conference_tty_enable(room_number):
    try:
        psap_app = PSAPApplication()
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

@conference.route('/tty/send/<room_number>', methods=['PUT', 'POST'])
def conference_tty_send(room_number):
    try:
        ttyData = get_argument('data')
        if (ttyData is None) or (ttyData == ''):
            raise ValueError('missing tty data to send')
        psap_app = PSAPApplication()
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

@conference.route('/tty/get/<room_number>', methods=['GET'])
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


@conference.route('/msrp/text/<room_number>', methods=['GET'])
def conference_msrp_text(room_number):
    try:
        log.debug("/msrp/text for room %s", room_number)
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

@conference.route('/msrp/send/<room_number>', methods=['PUT', 'POST'])
def conference_msrp_send(room_number):
    try:
        text = get_argument('text')
        sender = get_argument('sender')
        if (text is None) or (text == ''):
            raise ValueError('missing text to send')
        if (sender is None) or (sender == ''):
            raise ValueError('missing sender')
        psap_app = PSAPApplication()
        message_id, sender_uri = psap_app.send_msrp_text(room_number, sender, text)

        return jsonify({
            'success' : True,
            'message_id' : message_id,
            'sender_uri' : sender_uri
        })
    except Exception as e:
        stacktrace = traceback.print_exc()
        log.error("%r", stacktrace)
        log.error("conference_tty_send error %r", e)

        return jsonify ({
            'success' : False,
            'reason' : str(e)
        })


@conference.route('/event_log/<room_number>', methods=['GET'])
def conference_event_log(room_number):
    event_log_json = get_conference_event_log_json(room_number)

    response = {
        'success' : True,
        'event_log' : event_log_json
    }

    return jsonify(response)


@conference.route('/transfer_lines/<room_number>', methods=['GET'])
def get_call_transfer_lines(room_number):
    try:
        log.info('inside get_call_transfer_lines for room %s', room_number)
        psap_id = get_argument('psap_id')
        conf_db_obj = Conference.objects.get(room_number=room_number)
        if psap_id == None:
            psap_id = str(conf_db_obj.psap_id)
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
                    for call_transfer_line in CallTransferLine.objects(psap_id=psap_id, type=type):
                        transfer_lines.append({'name' : call_transfer_line.name, 'star_code' : call_transfer_line.star_code})
            else:
                for call_transfer_line in CallTransferLine.objects(psap_id=psap_id):
                    transfer_lines.append({'name': call_transfer_line.name, 'target': call_transfer_line.target})

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


@conference.route('/invite/<room_number>/<phone_number>', methods=['GET'])
def invite_to_conference(room_number, phone_number):
    try:
        psap_application = PSAPApplication()
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

@conference.route('/cancel_invite/<room_number>/<call_id>', methods=['GET'])
def cancel_invite_to_conference(room_number, call_id):
    try:
        psap_application = PSAPApplication()
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

@conference.route('/send_dtmf/<room_number>', methods=['GET', 'PUT', 'POST'])
def send_dtmf(room_number):
    try:
        dtmf = get_argument('dtmf')
        psap_application = PSAPApplication()
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


@conference.route('/transfer_line/<room_number>', methods=['GET', 'PUT', 'POST'])
def transfer_line(room_number):
    try:
        star_code = get_argument('star_code')
        psap_application = PSAPApplication()
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

