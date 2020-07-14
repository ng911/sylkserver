import logging
import time
from flask import Blueprint, jsonify
from flask_cors import CORS

from ..db.schema import User
from .decorators import check_exceptions
from .utils import get_argument
from ..data.calltaker import CalltakerData
status = Blueprint('status', __name__,
                        template_folder='templates')

CORS(status)

log = logging.getLogger('emergent-ng911')

@status.route('/test', methods=['GET'])
@check_exceptions
def test():
    response = {
        'success' : True,
        'message' : "hello tarun"
    }

    return jsonify(response)


@status.route('/<user_id>', methods=['POST', 'PUT'])
@check_exceptions
def update_status(user_id):
    status = get_argument('status')
    userObj = User.objects.get(user_id=user_id)
    userObj.status = status
    userObj.save()
    calltaker_data = CalltakerData()
    calltaker_data.update_status(user_id, status)

    response = {
        'success' : True,
        'update_time' : time.time()
    }

    return jsonify(response)

@status.route('/janus/<user_id>', methods=['POST', 'PUT'])
@check_exceptions
def update_janus_status(user_id):
    janus_busy = get_argument('janus_busy')
    calltaker_data = CalltakerData()
    log.info('inside update_janus_status calltaker %s, status %s', user_id, janus_busy)
    calltaker_data.update_janus_status(user_id, janus_busy)

    response = {
        'success': True,
        'update_time': time.time()
    }

    return jsonify(response)

