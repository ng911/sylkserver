import traceback
from flask import Blueprint, jsonify, request
from flask_cors import CORS, cross_origin
from sylk.configuration import ServerConfig
from sylk.applications import ApplicationLogger
from sylk.db.schema import User, CalltakerProfile, Psap
from sylk.data.calltaker import CalltakerData
from utils import get_argument
from sylk.utils import get_json_from_db_obj, set_db_obj_from_request

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
def get_status(user_id):
    calltaker_data = CalltakerData()
    status = calltaker_data.status(user_id)

    response = {
        'success' : True,
        'status' : status
    }

    return jsonify(response)

@calltaker.route('/status/<user_id>', methods=['POST', 'PUT'])
def update_status(user_id):
    status = get_argument('status')
    calltaker_data = CalltakerData()
    calltaker_data.update_status(user_id, status)

    response = {
        'success' : True
    }

    return jsonify(response)

@calltaker.route('/profile/<user_id>', methods=['GET'])
def get_profile(user_id):
    try:
        log.info("inside get_profile for %r", user_id)
        if (user_id is None) or (user_id == ''):
            raise ValueError('missing or invalid user_id')

        try:
            profile_obj = CalltakerProfile.objects.get(user_id=user_id)
        except:
            psap_db_obj = Psap.objects.get(psap_id=ServerConfig.psap_id)
            profile_obj = CalltakerProfile.objects.get(profile_id=psap_db_obj.default_profile_id)
        profile_json = get_json_from_db_obj(profile_obj, ignore_fields=['psap_id', 'user_id', 'profile_id'])
        response = {'success':True, 'profile':profile_json}
        return jsonify(response)
    except Exception as e:
        stacktrace = traceback.format_exc()
        log.error("%s", stacktrace)
        response = {
            'success' : False,
            'reason' : str(e)
        }

        return jsonify(response)

@calltaker.route('/profile/<user_id>', methods=['POST', 'PUT'])
def set_profile(user_id):
    try:
        if (user_id is None) or (user_id == ''):
            raise ValueError('missing or invalid user_id')

        try:
            profile_obj = CalltakerProfile.objects.get(user_id=user_id)
        except:
            profile_obj = CalltakerProfile()
            profile_obj.psap_id = ServerConfig.psap_id
            profile_obj.user_id = user_id

        set_db_obj_from_request(profile_obj, request)
        profile_obj.save()
        response = {'success':True, 'profile_id':str(profile_obj.profile_id)}
        return jsonify(response)
    except Exception as e:
        response = {
            'success' : False,
            'reason' : str(e)
        }

        return jsonify(response)

