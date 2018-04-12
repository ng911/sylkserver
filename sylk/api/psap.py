import traceback
import os
from sylk.configuration import ServerConfig
from flask import Blueprint, jsonify
from flask_cors import CORS, cross_origin
from sylk.applications import ApplicationLogger
from sylk.db.schema import User
from sylk.data.calltaker import CalltakerData
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
            log.info("path for sop found %r", path)
            try:
                with open(os.path.join(ServerConfig.sop_dir, name), 'r') as fp:
                    log.info("read sop file %r", name)
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
