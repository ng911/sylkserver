import traceback
import json
import time
import logging

from copy import deepcopy
from flask import Blueprint
from flask_cors import CORS
from flask_restful import reqparse
from ..db.schema import User, CalltakerProfile, Psap
from ..db.calltaker import add_update_calltaker, inactivate_calltaker
from .utils import get_argument
from ..utils import get_json_from_db_obj
from .decorators import check_exceptions


calltaker = Blueprint('calltaker', __name__,
                        template_folder='templates')

CORS(calltaker)

log = logging.getLogger("emergent-ng911")

'''
Note - for now we ignore the psap_id
'''
@calltaker.route('/all/<psap_id>', methods=['GET'])
@check_exceptions
def all(psap_id):
    users = []
    for user in User.objects(psap_id=psap_id, is_active=True):
        users.append(
            get_json_from_db_obj(user)
        )
    return {
        'users' : users
    }


@calltaker.route('/online/<psap_id>', methods=['GET'])
@check_exceptions
def online(psap_id):
    users = []
    for user in User.objects(psap_id=psap_id, is_active=True, status__in=['available', 'busy']):
        users.append(
            get_json_from_db_obj(user)
        )
    return {
        'users' : users
    }


@calltaker.route('/<user_id>', methods=['GET'])
@check_exceptions
def get(user_id):
    user_obj = User.objects.get(user_id=user_id)
    status = user_obj.status
    if (status is None) or (status == ''):
        status = 'offline'
    response = get_json_from_db_obj(user_obj)
    return response


def parse_calltaker_data():
    parser = reqparse.RequestParser()
    parser.add_argument('username', required=False)
    parser.add_argument('fullname', required=False)
    parser.add_argument('password', required=False)
    parser.add_argument('extension', required=False)
    parser.add_argument('auto_respond', type=bool, required=False)
    parser.add_argument('auto_respond_after', type=int, required=False)
    parser.add_argument('queues', action='append', required=False)
    parser.add_argument('role', required=False)
    parser.add_argument('psap_id', required=False)
    args = parser.parse_args()
    return args


@calltaker.route('/', methods=['POST', 'PUT'])
@check_exceptions
def newCalltaker():
    payload = parse_calltaker_data()
    response = add_update_calltaker(payload=payload, user_id=None)
    log.info("newCalltaker got response %r", response)
    return response


@calltaker.route('/<user_id>', methods=['POST', 'PUT'])
@check_exceptions
def updateCalltaker(user_id):
    payload = parse_calltaker_data()
    response = add_update_calltaker(payload=payload, user_id=user_id)
    return response


@calltaker.route('/inactivate/<user_id>', methods=['POST', 'PUT'])
@check_exceptions
def apiInactivateCalltaker(user_id):
    inactivate_calltaker(user_id)


@calltaker.route('/register/<user_id>', methods=['GET'])
@check_exceptions
def register(user_id):
    userObj = User.objects.get(user_id=user_id)
    userObj.status = 'available'
    userObj.save()

    response = {
    }

    return response


@calltaker.route('/status/<user_id>', methods=['GET'])
@check_exceptions
def get_status(user_id):
    userObj = User.objects.get(user_id=user_id)
    status = userObj.statususerObj.status
    if status is None:
        status = 'offline'

    response = {
        'success' : True,
        'status' : status,
        'update_time' : time.time()
    }

    return response


@calltaker.route('/status/<user_id>', methods=['POST', 'PUT'])
@check_exceptions
def update_status(user_id):
    status = get_argument('status')
    userObj = User.objects.get(user_id=user_id)
    userObj.status = status
    userObj.save()

    response = {
        'success' : True,
        'update_time' : time.time()
    }

    return response


@calltaker.route('/profile/<user_id>', methods=['GET'])
@check_exceptions
def get_profile(user_id):
    psap_id = get_argument('psap_id')
    log.info("inside get_profile for %r, psap_id %r", user_id, psap_id)
    if (user_id is None) or (user_id == ''):
        raise ValueError('missing or invalid user_id')
    if psap_id == None:
        try:
            userObj = User.objects.get(user_id=user_id)
            psap_id = str(userObj.psap_id)
        except:
            log.error("invalid user %r", user_id)
            return { "success" : False }
    profile_obj = None
    try:
        profile_obj = CalltakerProfile.objects.get(user_id=user_id)
    except:
        psap_db_obj = Psap.objects.get(psap_id=psap_id)
        try:
            profile_obj = CalltakerProfile.objects.get(profile_id=psap_db_obj.default_profile_id)
        except:
            pass
    if profile_obj != None:
        profile_json = get_json_from_db_obj(profile_obj, ignore_fields=['psap_id', 'user_id', 'profile_id'])
    else:
        profile_json = CalltakerProfile.get_default_profile()

    response = {'success':True, 'profile':profile_json}

    return response


@calltaker.route('/profile/<user_id>', methods=['POST', 'PUT'])
@check_exceptions
def set_profile(user_id):
    if (user_id is None) or (user_id == ''):
        raise ValueError('missing or invalid user_id')
    psap_id = get_argument('psap_id')
    log.info('inside set_profile for user {}'.format(user_id))
    str_json_data = get_argument('json')
    json_data = json.loads(str_json_data)
    log.info('inside set_profile jsonData is {}'.format(json_data))
    try:
        profile_obj = CalltakerProfile.objects.get(user_id=user_id)
        log.info('inside set_profile foud existing profile_obj {}'.format(profile_obj.profile_id))
    except:
        log.info('inside set_profile create new profile_obj')
        psap_db_obj = Psap.objects.get(psap_id=psap_id)
        profile_obj_psap = CalltakerProfile.objects.get(profile_id=psap_db_obj.default_profile_id)
        profile_obj = deepcopy(profile_obj_psap)
        profile_obj.id = None
        profile_obj.user_id = user_id

    for profile_name, val in json_data.items():
        setattr(profile_obj, profile_name, val)
    #set_db_obj_from_request(profile_obj, request)
    profile_obj.save()
    response = {'success':True, 'profile_id':str(profile_obj.profile_id)}
    return response

@calltaker.route('/layout/<user_id>', methods=['GET'])
@check_exceptions
def get_layout(user_id):
    userObj = User.objects.get(user_id=user_id)
    if hasattr(userObj, "layout") and userObj.layout != None and userObj.layout != {}:
        response = {
            'success': True,
            'layout' : userObj.layout
        }
    else:
        response = {
            'success': True,
            'layout': None
        }
    return response


@calltaker.route('/layout/<user_id>', methods=['POST', 'PUT'])
@check_exceptions
def update_layout(user_id):
    layout = get_argument('layout')
    userObj = User.objects.get(user_id=user_id)
    userObj.layout = layout
    userObj.save()

    response = {
        'success' : True,
        'update_time' : time.time()
    }

    return response

@calltaker.route('/layout/all/<psap_id>', methods=['POST', 'PUT'])
@check_exceptions
def update_layout_all(psap_id):
    layout = get_argument('layout')
    for userObj in User.objects(psap_id=psap_id):
        userObj.layout = layout
        userObj.save()

    response = {
        'success' : True,
        'update_time' : time.time()
    }

    return response
