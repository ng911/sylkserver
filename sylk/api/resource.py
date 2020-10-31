import logging
import os
import bson
import errno

from flask import Blueprint, current_app, send_from_directory, request, abort
from flask_cors import CORS
from flask_restful import reqparse
from werkzeug.utils import secure_filename

from ..db.queue import add_calltaker_to_queue, add_queue, get_queue_details, get_queue_members, \
    remove_calltaker_from_queue, remove_queue, edit_queue, get_queues
from .decorators import check_exceptions
from .utils import get_argument

resource = Blueprint('resource', __name__,
                        template_folder='templates')

CORS(resource)

log = logging.getLogger('emergent-ng911')

'''
@resource.route('/<resource_id>/<file_name>', methods=['GET'])
@check_exceptions
def get_file_from_resource_id(resource_id, file_name):
    """ GET a resource from resource_id and file name
        ---
        get:
            summary: get a resource.
            description: get a resource given psap id and resoure id
    """
    file_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], resource_id)
    return  send_from_directory(file_dir, file_name)
'''


@resource.route('/<psap_id>/maps/<resource_id>/<file_name>', methods=['GET'])
@check_exceptions
def get_resource_psap_maps(psap_id, resource_id, file_name):
    """ GET a resource
        ---
        get:
            summary: get a resource.
            description: get a resource given psap id and resoure id
    """
    subpath = os.path.join(psap_id, 'maps')
    subpath = os.path.join(subpath, resource_id)
    file_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], subpath)
    log.info("file_dir is %r", file_dir)
    log.info("file_name is %r", file_name)
    return  send_from_directory(file_dir, file_name)


@resource.route('/<psap_id>/<sub_folder>/<file_name>', methods=['GET'])
@check_exceptions
def get_resource_psap(psap_id, sub_folder, file_name):
    """ GET a resource
        ---
        get:
            summary: get a resource.
            description: get a resource given psap id and resoure id
    """
    subpath = os.path.join(psap_id, sub_folder)
    file_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], subpath)
    return  send_from_directory(file_dir, file_name)


@resource.route('/process', methods=['POST'])
def add_resource():
    """ GET a resource
        ---
        get:
            summary: get a resource.
            description: get a resource given psap id and resoure id
    """
    resource_id = str(bson.ObjectId())
    log.info("request is %r", request)
    log.info("request.files is %r", request.files)

    if 'files' not in request.files:
        log.error("add_resource no fille in request")
        log.error("add_resource request.files is %r, %s, length is %d", request.files, str(request.files), len(request.files))
        for name in request.files:
            log.info("found %r, %s", name, str(name))
        abort(400, 'No file part')

    files = request.files['files']
    log.info("files is %r", files)
    if files.filename == '':
        abort(400, 'No selected file')

    filename = secure_filename(files.filename)
    file_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], resource_id)
    try:
        os.makedirs(file_dir)
    except OSError as exc:  # Guard against race condition
        if exc.errno != errno.EEXIST:
            abort(400, 'error in creating directory ')
    files.save(os.path.join(file_dir, filename))
    return resource_id

