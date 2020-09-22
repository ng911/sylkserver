import logging
import os

from flask import Blueprint, current_app, send_from_directory
from flask_cors import CORS
from flask_restful import reqparse

from ..db.queue import add_calltaker_to_queue, add_queue, get_queue_details, get_queue_members, \
    remove_calltaker_from_queue, remove_queue, edit_queue, get_queues
from .decorators import check_exceptions
from .utils import get_argument

resource = Blueprint('resource', __name__,
                        template_folder='templates')

CORS(resource)

log = logging.getLogger('emergent-ng911')


@resource.route('/<psap_id>/<sub_folder>/<file_name>', methods=['GET'])
@check_exceptions
def get_resource(psap_id, sub_folder, file_name):
    """ GET a resource
        ---
        get:
            summary: get a resource.
            description: get a resource given psap id and resoure id
    """
    subpath = os.path.join(psap_id, sub_folder)
    file_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], subpath)
    return  send_from_directory(file_dir, file_name)

