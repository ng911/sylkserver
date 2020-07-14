import logging
import os
import traceback

from flask import Blueprint, jsonify
from flask_cors import CORS

from ..db.schema import SpeedDial, Greeting, CallTransferLine, Psap
from ..utils import get_json_from_db_obj
from .utils import get_argument
from ..config import SOP_DIR

psap = Blueprint('psap', __name__,
                        template_folder='templates')

CORS(psap)

log = logging.getLogger("emergent-ng911")


# read SOP files and create the data structure for the client
def read_sops():
    mapping, type1, type2 = {}, [''], {}
    for name in os.listdir(SOP_DIR):
        path = os.path.join(SOP_DIR, name)
        if os.path.exists(path) and os.path.isfile(path):
            try:
                with open(os.path.join(SOP_DIR, name), 'r') as fp:
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


@psap.route('/', methods=['GET'])
def getPsaps():
    try:
        log.info("inside getPsaps")

        psaps = []
        for psapObj in Psap.objects():
            psaps.append(
                get_json_from_db_obj(psapObj)
            )

        log.info("inside getPsaps psaps is %r", psaps)
        return jsonify({
            "psaps" : psaps
        })
    except Exception as e:
        stacktrace = traceback.format_exc()
        log.info("inside getPsaps got exception")
        log.error(stacktrace)
        log.error(e.message)


@psap.route('/<psap_id>', methods=['GET'])
def getPsap(psap_id):
    try:
        log.info("inside getPsaps for psap %r", psap_id)

        return jsonify(
            get_json_from_db_obj(
                Psap.objects.get(psap_id=psap_id)
            )
        )
    except Exception as e:
        stacktrace = traceback.format_exc()
        log.info("inside getPsap got exception")
        log.error(stacktrace)
        log.error(e.message)

'''
@psap.route('/speed_dial', methods=['GET'])
def speed_dial():
    try:
        speed_dials = []
        params = {'psap_id' : ServerConfig.psap_id}
        params['user_id__exists'] = False
        speed_dial_cursor = SpeedDial.objects(**params)
        for speed_dial_db_obj in speed_dial_cursor:
            speed_dial = get_json_from_db_obj(speed_dial_db_obj, ignore_fields=['psap_id', 'user_id'])
            speed_dial['type'] = 'psap'
            speed_dials.append(speed_dial)

        user_id = get_argument('user_id')
        if user_id is not None:
            params = {'psap_id': ServerConfig.psap_id}
            params['user_id'] = user_id
            speed_dial_cursor = SpeedDial.objects(**params)
            for speed_dial_db_obj in speed_dial_cursor:
                speed_dial = get_json_from_db_obj(speed_dial_db_obj, ignore_fields=['psap_id', 'user_id'])
                speed_dial['type'] = 'calltaker'
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
        user_id = get_argument('user_id')
        name = get_argument('name')
        number = get_argument('number')
        log.info('inside update speed dial, user_id %r, name %r, number %r', user_id, name, number)
        try:
            speedDialObj = SpeedDial.objects.get(user_id=user_id, name=name)
        except:
            speedDialObj = SpeedDial()
            speedDialObj.name = name
            speedDialObj.user_id = user_id
            speedDialObj.psap_id = ServerConfig.psap_id

        speedDialObj.dest = number
        speedDialObj.save()
        return jsonify(result)
    except Exception as e:
        result = {'success' : False, 'reason' : str(e)}
        return jsonify(result)


@psap.route('/speed_dial', methods=['DELETE'])
def delete_speed_dial():
    try:
        log.info('inside delete speed dial')
        user_id = get_argument('user_id')
        name = get_argument('name')
        log.info('inside delete speed dial, user_id %r, name %r', user_id, name)
        speedDialObj = SpeedDial.objects.get(user_id=user_id, name=name)
        speedDialObj.delete()
        result = {'success': True}
        return jsonify(result)
    except Exception as e:
        result = {'success' : False, 'reason' : str(e)}
        return jsonify(result)
'''

@psap.route('/greetings/<psap_id>', methods=['GET'])
def greetings(psap_id):
    try:
        user_id = get_argument('user_id')
        params = {'psap_id' : psap_id}
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


@psap.route('/call_transfer_lines/<psap_id>', methods=['GET'])
def call_transfer_lines(psap_id):
    try:
        call_transfer_lines = []
        for call_transfer_line_obj in CallTransferLine.objects(psap_id=psap_id):
            call_transfer_line = get_json_from_db_obj(call_transfer_line_obj, ignore_fields=['psap_id'])
            call_transfer_lines.append(call_transfer_line)

        result = {'success': True, 'call_transfer_lines' : call_transfer_lines}
        return jsonify(result)
    except Exception as e:
        result = {'success' : False, 'reason' : str(e)}
        return jsonify(result)

