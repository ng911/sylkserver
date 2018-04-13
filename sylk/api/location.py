import traceback
import datetime
from flask import Blueprint, jsonify, request
from flask_cors import CORS
from sylk.applications import ApplicationLogger
from sylk.db.schema import Location
from utils import get_argument
from sylk.utils import get_json_from_db_obj, set_db_obj_from_request

location = Blueprint('location', __name__,
                        template_folder='templates')

CORS(location)
log = ApplicationLogger(__package__)


@location.route('/<room_number>', methods=['GET'])
def get_location(room_number):
    try:
        page_no = get_argument('page', 0)
        params = {'room_number' : room_number}

        count = Location.objects(**params).count()

        if count > 0:
            location_db_obj = Location.objects(room_number=room_number).order_by('-time')[page_no:1]
            location_json = get_json_from_db_obj(location_db_obj)
        else:
            location_json = {}

        response = {'success' : True, 'total_records' : count, 'page' : page_no, 'location' : location_json}
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
        location_db_obj = Location.objects(location_id=location_id)
        set_db_obj_from_request(location_db_obj, request)
        location_db_obj.descrepancy = True
        location_db_obj.updated_at = datetime.datetime.utcnow()
        location_db_obj.save()
        response = {'success' : True}
        return jsonify(response)
    except Exception as e:
        stacktrace = traceback.format_exc()
        log.error("api location %r", e)
        log.error(stacktrace)
        response = {'success' : False, 'reason' : str(e)}
        return jsonify(response)


