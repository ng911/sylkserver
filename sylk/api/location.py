import traceback
import datetime
import logging

from flask import Blueprint, jsonify, request
from flask_cors import CORS

from ..db.schema import Location, Conference
from ..db.location import get_location_display
from .utils import get_argument
from ..utils import get_json_from_db_obj, set_db_obj_from_request
import sylk.location

location = Blueprint('location', __name__,
                        template_folder='templates')

CORS(location)

log = logging.getLogger("emergent-ng911")

@location.route('/<room_number>', methods=['GET'])
def get_location(room_number):
    try:
        page_no = get_argument('page', 0)
        params = {'room_number' : room_number}

        count = Location.objects(**params).count()

        if count > 0:
            location_db_obj = Location.objects(room_number=room_number).order_by('-updated_at')[page_no]
            location_json = get_json_from_db_obj(location_db_obj)
            location_display = get_location_display(location_db_obj)
        else:
            location_json = {}
            location_display = ''

        response = {'success' : True, 'total_records' : count, 'page' : page_no, 'location' : location_json, 'location_display': location_display}
        return jsonify(response)
    except Exception as e:
        stacktrace = traceback.format_exc()
        log.error("api location %r", e)
        log.error(stacktrace)
        response = {'success' : False, 'reason' : str(e)}
        return jsonify(response)


@location.route('/<location_id>', methods=['PUT', 'POST'])
def set_location(location_id):
    try:
        location_db_obj = Location.objects.get(location_id=location_id)
        set_db_obj_from_request(location_db_obj, request, ignore_fields=['updated_at', 'time'])
        location_db_obj.descrepancy = True
        location_db_obj.updated_at = datetime.datetime.utcnow()
        location_db_obj.save()
        location_display = get_location_display(location_db_obj)
        room_number = location_db_obj.room_number
        if (room_number is not None) and (room_number != ''):
            conference_db_obj = Conference.objects.get(room_number=room_number)
            conference_db_obj.location_display = location_display
            conference_db_obj.save()
        response = {'success' : True, 'location_display' : location_display}
        return jsonify(response)
    except Exception as e:
        stacktrace = traceback.format_exc()
        log.error("api location %r", e)
        log.error(stacktrace)
        response = {'success' : False, 'reason' : str(e)}
        return jsonify(response)


@location.route('/display/<room_number>', methods=['GET'])
def get_call_location_display(room_number):
    try:
        location_db_obj = Location.objects(room_number=room_number).order_by('-updated_at')[0]

        response = {'success' : True, 'display' : get_location_display(location_db_obj)}
        return jsonify(response)
    except Exception as e:
        stacktrace = traceback.format_exc()
        log.error("api location %r", e)
        log.error(stacktrace)
        response = {'success' : False, 'reason' : str(e)}
        return jsonify(response)


@location.route('/query/<room_number>', methods=['GET', 'POST', 'PUT'])
def do_ali_query(room_number):
    try:
        ali_format = get_argument('ali_format')
        lookup_number = get_argument('lookup_number')

        trans_id = sylk.location.ali_lookup(room_number, str(lookup_number), ali_format)
        response = {'success' : True, 'trans_id' : trans_id}
        return jsonify(response)
    except Exception as e:
        stacktrace = traceback.format_exc()
        log.error("api location %r", e)
        log.error(stacktrace)
        response = {'success' : False, 'reason' : str(e)}
        return jsonify(response)

