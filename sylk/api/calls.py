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
            'conf-id' : '1123',
            'call-type' : 'sos',
            'media' : ['voice'],
            'ani' : '4153054541',
            'name' : 'tarun',
            'location' : '665 pine str, san francisco, california',
            'note' : 'his pet is not feeling well',
            'date-time' : '9:15 am, Mar 12',
            'status' : 'ringing'
        },
        {
            'conf-id': '1124',
            'call-type': 'sos',
            'media': ['voice'],
            'ani': '4153054541',
            'name': 'mike',
            'location': '665 pine str, san francisco, california',
            'note': '',
            'date-time': '9:00 am, Mar 12',
            'status': 'active'
        },
        {
            'conf-id': '1125',
            'call-type': 'sos',
            'media': ['voice'],
            'ani': '6503054542',
            'name': 'nate',
            'location': '665 pine str, san mateo, california',
            'note': 'saw robbery',
            'date-time': '8:45 am, Mar 12',
            'status': 'active'
        },
        {
            'conf-id': '1126',
            'call-type': 'sos',
            'media': ['voice'],
            'ani': '4153054541',
            'name': 'tarun',
            'location': '665 pine str, san francisco, california',
            'note': '',
            'date-time': '8:00 am, Mar 12',
            'status': 'abandoned'
        },
        {
            'conf-id': '1127',
            'call-type': 'sos',
            'media': ['voice'],
            'ani': '4153054541',
            'name': 'matt',
            'location': '665 pine str, santa clara, california',
            'note': '',
            'date-time': '7:30 am, Mar 12',
            'status': 'abandoned'
        },
        {
            'conf-id': '1128',
            'call-type': 'sos',
            'media': ['text'],
            'ani': '415551212',
            'name': 'tom sawyer',
            'location': '665 pine str, san jose, california',
            'note': '',
            'date-time': '7:15 am, Mar 12',
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
            'conf-id' : '2123',
            'call-type' : 'sos',
            'media' : ['voice'],
            'ani' : '4153054541',
            'name' : 'tom sawyer',
            'location' : '665 pine str, san francisco, california',
            'note' : 'prank call',
            'date-time' : '9:15 am, Mar 12',
            'status' : 'closed'
        },
        {
            'conf-id': '2124',
            'call-type': 'sos',
            'media': ['voice'],
            'ani': '4153054541',
            'name': 'tarun',
            'location': '665 pine str, san francisco, california',
            'note': 'son not well',
            'date-time': '9:00 am, Mar 12',
            'status': 'callback'
        },
        {
            'conf-id': '1125',
            'call-type': 'sos',
            'media': ['voice'],
            'ani': '6503054542',
            'name': 'michael jordon',
            'location': '665 pine str, san jose, california',
            'note': 'fire in apartment',
            'date-time': '8:45 am, Mar 12',
            'status': 'closed'
        },
        {
            'conf-id': '1126',
            'call-type': 'sos',
            'media': ['voice'],
            'ani': '4153054541',
            'name': 'steph curry',
            'location': '665 pine str, monterey, california',
            'note': '',
            'date-time': '8:00 am, Mar 12',
            'status': 'abandoned'
        },
        {
            'conf-id': '1127',
            'call-type': 'sos',
            'media': ['voice'],
            'ani': '4153054541',
            'name': 'nate',
            'location': '665 pine str, san francisco, california',
            'note': 'his pet is not feeling well',
            'date-time': '7:30 am, Mar 12',
            'status': 'abandoned'
        },
        {
            'conf-id': '1128',
            'call-type': 'sos',
            'media': ['text'],
            'ani': '415551212',
            'name': 'tarun',
            'location': '665 pine str, mountain view, california',
            'note': 'his pet is not feeling well',
            'date-time': '7:15 am, Mar 12',
            'status': 'closed'
        }
    ]
    response = {
        'success' : True,
        'calls' : calls
    }

    return jsonify(response)


