import traceback
from flask import Blueprint, jsonify
from flask_cors import CORS, cross_origin
from sylk.applications import ApplicationLogger
from sylk.db.schema import User
from sylk.data.calltaker import CalltakerData
from utils import get_argument

calltaker = Blueprint('calltaker', __name__,
                        template_folder='templates')

CORS(calltaker)
log = ApplicationLogger(__package__)

'''
Note - for now we ignore the psap_id
'''
@calltaker.route('/', methods=['GET'])
def all():
    calltaker_data = CalltakerData()
    response = {
        'success' : True,
        'calltakers' : calltaker_data.calltakers
    }

    return jsonify(response)

@calltaker.route('/online', methods=['GET'])
def online():
    calltaker_data = CalltakerData()
    response = {
        'success' : True,
        'calltakers' : calltaker_data.available_calltakers
    }

    return jsonify(response)

@calltaker.route('/<user_id>', methods=['GET'])
def get(user_id):
    user_obj = User.objects.get(user_id=user_id)
    calltaker_data = CalltakerData()
    status = calltaker_data.status(user_id)
    if status is None:
        status = 'offline'
    response = {'success' : True}
    response['username'] = user_obj.username
    response['status'] = status
    response['user_id'] = user_id
    response.append(calltaker)
    return jsonify(response)


@calltaker.route('/register/<user_id>', methods=['GET'])
def register(user_id):
    calltaker_data = CalltakerData()
    calltaker_data.update_status(user_id, 'online')

    response = {
        'success' : True
    }

    return jsonify(response)


@calltaker.route('/status/<user_id>', methods=['GET'])
def getStatus(user_id):
    calltaker_data = CalltakerData()
    status = calltaker_data.status(user_id)

    response = {
        'success' : True,
        'status' : status
    }

    return jsonify(response)

@calltaker.route('/status/<user_id>', methods=['POST', 'PUT'])
def updateStatus(user_id):
    status = get_argument('status')
    calltaker_data = CalltakerData()
    calltaker_data.update_status(user_id, status)

    response = {
        'success' : True
    }

    return jsonify(response)
