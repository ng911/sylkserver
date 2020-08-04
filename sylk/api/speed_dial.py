import logging
from flask import Blueprint, jsonify
from flask_cors import CORS
from flask_restful import reqparse

from ..db.speed_dial import get_speed_dial_groups, get_speed_dials, add_speed_dial_group, \
    remove_speed_dial_group, edit_speed_dial_group, add_speed_dial, remove_speed_dial, \
    get_speed_dial, edit_speed_dial, get_user_speed_dials
from .decorators import check_exceptions

speed_dial = Blueprint('speed_dial', __name__,
                        template_folder='templates')

CORS(speed_dial)

log = logging.getLogger('emergent-ng911')


@speed_dial.route('/all/<psap_id>', methods=['GET'])
@check_exceptions
def all(psap_id):
    parser = reqparse.RequestParser()
    parser.add_argument('group_name', required=False)
    payload = parser.parse_args()
    return {
        "speed_dials" : get_speed_dials(psap_id, payload['group_name'])
    }

@speed_dial.route('/user/<user_id>', methods=['GET'])
@check_exceptions
def user_speed_dials(user_id):
    return {
        "speed_dials" : get_user_speed_dials(user_id)
    }

@speed_dial.route('/<speed_dial_id>', methods=['GET'])
@check_exceptions
def api_get_speed_dial(speed_dial_id):
    return get_speed_dial(speed_dial_id)


@speed_dial.route('/<speed_dial_id>', methods=['POST', 'PUT'])
@check_exceptions
def api_edit_speed_dial(speed_dial_id):
    parser = reqparse.RequestParser()
    parser.add_argument('name', required=False)
    parser.add_argument('dest', required=False)
    payload = parser.parse_args()
    edit_speed_dial(speed_dial_id, payload)


@speed_dial.route('/add', methods=['POST', 'PUT'])
@check_exceptions
def api_add_speed_dial():
    parser = reqparse.RequestParser()
    parser.add_argument('group_id', required=False)
    parser.add_argument('dest', required=True)
    parser.add_argument('name', required=True)
    parser.add_argument('psap_id', required=True)
    parser.add_argument('show_as_button', required=False)
    parser.add_argument('icon', required=False)
    parser.add_argument('files', required=False)
    payload = parser.parse_args()
    return add_speed_dial(payload['psap_id'], payload['dest'], payload['name'], payload['group_id'], payload['show_as_button'], payload['icon'], payload['files'])


@speed_dial.route('/delete/<speed_dial_id>', methods=['POST', 'PUT'])
@check_exceptions
def api_delete_speed_dial(speed_dial_id):
    remove_speed_dial(speed_dial_id)


@speed_dial.route('/groups/<psap_id>', methods=['GET'])
@check_exceptions
def api_get_groups(psap_id):
    return {
        "groups" : get_speed_dial_groups(psap_id)
    }


@speed_dial.route('/group/<group_id>', methods=['POST', 'PUT'])
@check_exceptions
def api_edit_group(group_id):
    parser = reqparse.RequestParser()
    parser.add_argument('group_name', required=True)
    payload = parser.parse_args()
    edit_speed_dial_group(group_id, payload["group_name"])


@speed_dial.route('/group/add', methods=['POST', 'PUT'])
@check_exceptions
def api_add_group():
    parser = reqparse.RequestParser()
    parser.add_argument('group_name', required=True)
    parser.add_argument('psap_id', required=True)
    payload = parser.parse_args()
    return add_speed_dial_group(payload["psap_id"], payload["group_name"])


@speed_dial.route('/group/delete/<group_id>', methods=['POST', 'PUT'])
@check_exceptions
def api_delete_group(group_id):
    remove_speed_dial_group(group_id)





