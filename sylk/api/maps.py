import logging
import os
import bson
import errno
from flask import Blueprint, request, abort, current_app, url_for
from flask_cors import CORS
from flask_restful import reqparse
from werkzeug.utils import secure_filename

from ..db.schema import MapFile
from .decorators import check_exceptions
from .utils import get_argument

maps = Blueprint('maps', __name__,
                        template_folder='templates')

CORS(maps)

log = logging.getLogger('emergent-ng911')

def save_file(psap_id, subdir, file):
    filename = secure_filename(file.filename)
    filename_no_ext, file_extension = os.path.splitext(filename)
    if len(file_extension) > 0:
        format = file_extension[1:]
    else:
        format = ""
    subpath = os.path.join(psap_id, subdir)
    file_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], subpath)
    try:
        os.makedirs(file_dir)
    except OSError as exc:  # Guard against race condition
        if exc.errno != errno.EEXIST:
            abort(400, 'error in creating directory ')
    file.save(os.path.join(file_dir, filename))
    log.info('file_dir %s, filename %s', file_dir, filename)
    file_path = os.path.join(file_dir, filename)
    log.info('file_path %s', file_path)
    return subpath, filename


@maps.route('/add', methods=['POST'])
@check_exceptions
def add_map_file():
    """ Add a map file
        ---
        post:
            summary: Add a resource.
            description: Add a resource. along with params listed below you need to pass a file object containing the file
            parameters:
                - in: body
                  schema: AddResourceInputSchema
            responses:
                200:
                    description: object to be returned.
                    schema: AddResourceResponseSchema
    """
    # check if the post request has the file part
    log.info("inside add_map_file ")
    if 'file' not in request.files:
        log.error("add_resource no fille in request")
        log.error("add_resource request.files is %r, %s, length is %d", request.files, str(request.files), len(request.files))
        for name in request.files:
            log.info("found %r, %s", name, str(name))
        abort(400, 'No file part')

    file = request.files['file']
    psap_id = get_argument('psap_id')
    # if user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
        abort(400, 'No selected file')

    map_file_id = str(bson.ObjectId())
    subpath, filename = save_file(psap_id, "maps", file)
    log.info("inside add_map_file subpath %r, filename %r", subpath, filename)

    url_endpoint = "resource/%s/%s" % (subpath, filename)
    file_url = url_for(url_endpoint)
    map_file = MapFile(map_file_id=map_file_id, psap_id = psap_id, map_file = filename, map_file_dir = subpath)
    map_file.save()
    return {
        'success' : True,
        "file_url" : file_url,
        'map_file_id' : str(map_file_id),
    }




