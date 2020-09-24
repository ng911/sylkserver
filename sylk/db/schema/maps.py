import logging
import bson
from mongoengine import *

from .core import graphql_node_notifications

# from werkzeug.security import generate_password_hash, check_password_hash
log = logging.getLogger("emergent-ng911")


@graphql_node_notifications
class MapLayer(Document):
    map_layer_id = ObjectIdField(required=True, default=bson.ObjectId, unique=True)
    psap_id = ObjectIdField(required=True)
    description = StringField(required=True)
    meta = {
        'indexes': [
            'map_layer_id',
            'psap_id'
        ]
    }


@graphql_node_notifications
class MapFile(Document):
    map_layer_id = ObjectIdField(required=True)
    map_file_id = ObjectIdField(required=True, default=bson.ObjectId, unique=True)
    psap_id = ObjectIdField(required=True)
    filename = StringField(required=True)
    relative_path = StringField(required=True)
    meta = {
        'indexes': [
            'map_layer_id',
            'map_file_id',
            'psap_id'
        ]
    }



