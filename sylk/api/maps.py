import logging
import os
from os import listdir
from os.path import isfile, join
import bson
import errno
from flask import Blueprint, request, abort, current_app, url_for
from flask_cors import CORS
from flask_restful import reqparse
from werkzeug.utils import secure_filename

from ..db.schema import MapFile, MapLayer
from .decorators import check_exceptions
from .utils import get_argument

maps = Blueprint('maps', __name__,
                        template_folder='templates')

CORS(maps)

log = logging.getLogger('emergent-ng911')
maps_subdir = 'maps'

'''
def save_map_file(psap_id, map_layer_id, file):
    filename = secure_filename(file.filename)
    subpath = os.path.join(psap_id, maps_subdir)
    subpath = os.path.join(subpath, map_layer_id)
    file_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], subpath)
    try:
        os.makedirs(file_dir)
    except OSError as exc:  # Guard against race condition
        if exc.errno != errno.EEXIST:
            abort(400, 'error in creating directory ')
    file.save(os.path.join(file_dir, filename))
    log.info('file_dir %s, filename %s', file_dir, filename)
    return subpath, filename
'''
def get_filename(server_file_id):
    tmp_file_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], server_file_id)
    onlyfiles = [f for f in listdir(tmp_file_dir) if isfile(join(tmp_file_dir, f))]
    filename = onlyfiles[0]
    filepath = os.path.join(tmp_file_dir, filename)
    return tmp_file_dir, filepath, filename


def save_map_file(psap_id, map_layer_id, server_file_id):
    tmp_path, tmp_file_with_path, filename = get_filename(server_file_id)
    subpath = os.path.join(psap_id, maps_subdir)
    subpath = os.path.join(subpath, map_layer_id)
    file_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], subpath)
    try:
        os.makedirs(file_dir)
    except OSError as exc:  # Guard against race condition
        if exc.errno != errno.EEXIST:
            abort(400, 'error in creating directory ')
    dest_file_with_path = os.path.join(file_dir, filename)
    os.rename(tmp_file_with_path, dest_file_with_path)
    os.rmdir(tmp_path)
    log.info('file_dir %s, filename %s', file_dir, filename)
    return subpath, filename


@maps.route('/layer/add', methods=['POST'])
@check_exceptions
def add_map_layer():
    psap_id = get_argument('psap_id')
    description = get_argument('description')
    map_layer = MapLayer(psap_id=psap_id, description=description)
    map_layer.save()
    map_layer_id = str(map_layer.map_layer_id)
    return {
        "success" : True,
        "map_layer_id" : map_layer_id
    }



@maps.route('/layer/edit/<map_layer_id>', methods=['POST'])
@check_exceptions
def edit_map_layer(map_layer_id):
    description = get_argument('description')
    map_layer = MapLayer.objects.get(map_layer_id=map_layer_id)
    map_layer.description = description
    map_layer.save()
    return {
        "success" : True,
    }


@maps.route('/layer/delete/<map_layer_id>', methods=['POST'])
@check_exceptions
def delete_map_layer(map_layer_id):
    for mapfile in MapFile.objects(map_layer_id=map_layer_id):
        delete_map_file(mapfile.relative_path, mapfile.filename)
    MapFile.objects(map_layer_id=map_layer_id).delete()
    MapLayer.objects.get(map_layer_id=map_layer_id).delete()

    return {
        "success" : True,
    }


@maps.route('/layer/files/add', methods=['POST'])
@check_exceptions
def add_map_files():
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
    '''
    if 'file' not in request.files:
        log.error("add_resource no fille in request")
        log.error("add_resource request.files is %r, %s, length is %d", request.files, str(request.files), len(request.files))
        for name in request.files:
            log.info("found %r, %s", name, str(name))
        abort(400, 'No file part')
    '''
    server_file_ids = get_argument('server_file_ids', [])
    psap_id = get_argument('psap_id')
    map_layer_id = get_argument('map_layer_id')
    if map_layer_id is None:
        description = get_argument('description')
        map_layer = MapLayer(psap_id=psap_id, description=description)
        map_layer.save()
        map_layer_id = str(map_layer.map_layer_id)


    #uploaded_files = request.files.getlist("file[]")
    log.info("inside add_map_file map_layer_id %r", map_layer_id)
    # file = request.files['file']
    for server_file_id in server_file_ids:
        # if user does not select file, browser also
        # submit an empty part without filename
        log.info("inside add_map_file got file id %r", server_file_id)
        subpath, filename = save_map_file(psap_id, map_layer_id, server_file_id)
        log.info("inside add_map_file subpath %r, filename %r", subpath, filename)
        #url_endpoint = "resource/%s/%s" % (subpath, filename)
        #file_url = url_for(url_endpoint)
        map_file = MapFile(map_layer_id=map_layer_id, psap_id = psap_id, filename = filename, relative_path = subpath)
        map_file.save()
    return {
        'success' : True
    }

def delete_map_file(relative_path, filename):
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], relative_path)
    file_with_path = os.path.join(filepath, filename)
    os.remove(file_with_path)


@maps.route('/layer/files/delete', methods=['POST'])
@check_exceptions
def delete_map_files():
    delete_all = get_argument('delete_all')
    map_layer_id = get_argument('map_layer_id')
    if delete_all != None and not delete_all:
        filename = get_argument('filename')
        mapfile = MapFile.objects.get(map_layer_id=map_layer_id, filename=filename)
        delete_map_file(mapfile.relative_path, filename)
        mapfile.delete()
    else:
        for mapfile in MapFile.objects(map_layer_id = map_layer_id):
            delete_map_file(mapfile.relative_path, mapfile.filename)
        MapFile.objects(map_layer_id = map_layer_id).delete()


