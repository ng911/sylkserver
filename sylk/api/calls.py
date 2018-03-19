import traceback
from flask import Blueprint, jsonify
from flask_cors import CORS, cross_origin
from sylk.applications import ApplicationLogger
from sylk.db.schema import User
from sylk.data.calltaker import CalltakerData

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
    response = {
        'success' : True,
        'calls' : calls
    }

    return jsonify(response)


