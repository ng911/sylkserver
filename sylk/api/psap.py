import traceback
import os
from sylk.configuration import ServerConfig
from flask import Blueprint, jsonify
from flask_cors import CORS, cross_origin
from sylk.applications import ApplicationLogger
from sylk.db.schema import SpeedDial, Greeting, CallTransferLine
from sylk.utils import get_json_from_db_obj
from utils import get_argument

psap = Blueprint('psap', __name__,
                        template_folder='templates')

CORS(psap)
log = ApplicationLogger(__package__)


# read SOP files and create the data structure for the client
def read_sops():
    mapping, type1, type2 = {}, [''], {}
    for name in os.listdir(ServerConfig.sop_dir):
        path = os.path.join(ServerConfig.sop_dir, name)
        if os.path.exists(path) and os.path.isfile(path):
            try:
                with open(os.path.join(ServerConfig.sop_dir, name), 'r') as fp:
                    # logger.debug('sop file %r', fp)
                    parts = fp.read().split('----')
                    t1, t2, description = parts[0].strip().split(' ', 2)
                    agencies = parts[1].strip().split(' ')
                    sop, script = parts[2].strip(), parts[3].strip()
                    if t1 not in mapping:
                        mapping[t1] = {}
                        type1.append(t1)
                        type2[t1] = ['']
                    if t2 not in type2[t1]:
                        type2[t1].append(t2)
                    mapping[t1][t2] = dict(description=description, agencies=agencies, sop=sop, script=script)
            except:
                log.exception('failed to read SOP %r', name)
        else:
            log.error("check if path %r is correct ", path)
    result = dict(mapping=mapping, type1=type1, type2=type2)
    # logger.debug('result=%r', result)
    return result


'''
Note - for now we ignore the psap_id
'''
@psap.route('/sops', methods=['GET'])
def sops():
    sops = read_sops()
    sops['success'] = True

    return jsonify(sops)


@psap.route('/speed_dial', methods=['GET'])
def speed_dial():
    try:
        speed_dials = []
        params = {'psap_id' : ServerConfig.psap_id}
        params['user_id__exists'] = False
        speed_dial_cursor = SpeedDial.objects(**params)
        for speed_dial_db_obj in speed_dial_cursor:
            speed_dial = get_json_from_db_obj(speed_dial_db_obj, ignore_fields=['psap_id', 'user_id'])
            speed_dials.append(speed_dial)

        user_id = get_argument('user_id')
        if user_id is not None:
            params = {'psap_id': ServerConfig.psap_id}
            params['user_id'] = user_id
            speed_dial_cursor = SpeedDial.objects(**params)
            for speed_dial_db_obj in speed_dial_cursor:
                speed_dial = get_json_from_db_obj(speed_dial_db_obj, ignore_fields=['psap_id', 'user_id'])
                speed_dials.append(speed_dial)

        result = {'success': True, 'speed_dials' : speed_dials}
        return jsonify(result)
    except Exception as e:
        result = {'success' : False, 'reason' : str(e)}
        return jsonify(result)


@psap.route('/speed_dial', methods=['PUT', 'POST'])
def update_speed_dial():
    try:
        log.info('inside update speed dial')
        result = {'success': True}
        return jsonify(result)
    except Exception as e:
        result = {'success' : False, 'reason' : str(e)}
        return jsonify(result)


@psap.route('/speed_dial', methods=['DELETE'])
def delete_speed_dial():
    try:
        log.info('inside delete speed dial')
        result = {'success': True}
        return jsonify(result)
    except Exception as e:
        result = {'success' : False, 'reason' : str(e)}
        return jsonify(result)


@psap.route('/greetings', methods=['GET'])
def greetings():
    try:
        user_id = get_argument('user_id')
        params = {'psap_id' : ServerConfig.psap_id}
        if user_id is None:
            params['user_id__exists'] = False
        else:
            params['user_id'] = user_id
        greeting_cursor = Greeting.objects(**params)
        greetings = []
        for greeting_db_obj in greeting_cursor:
            greeting = get_json_from_db_obj(greeting_db_obj, ignore_fields=['psap_id', 'user_id'])
            greetings.append(greeting)

        result = {'success': True, 'greetings' : greetings}
        return jsonify(result)
    except Exception as e:
        result = {'success' : False, 'reason' : str(e)}
        return jsonify(result)


@psap.route('/call_transfer_lines', methods=['GET'])
def call_transfer_lines():
    try:
        call_transfer_lines = []
        for call_transfer_line_obj in CallTransferLine.objects(psap_id=ServerConfig.psap_id):
            call_transfer_line = get_json_from_db_obj(call_transfer_line_obj, ignore_fields=['psap_id'])
            call_transfer_lines.append(call_transfer_line)

        result = {'success': True, 'call_transfer_lines' : call_transfer_lines}
        return jsonify(result)
    except Exception as e:
        result = {'success' : False, 'reason' : str(e)}
        return jsonify(result)

