import logging
import bson
from mongoengine import *

from .core import graphql_node_notifications

# from werkzeug.security import generate_password_hash, check_password_hash
log = logging.getLogger("emergent-ng911")

@graphql_node_notifications
class MapFile(Document):
    map_file_id = ObjectIdField(required=True, default=bson.ObjectId, unique=True)
    psap_id = ObjectIdField(required=True)
    map_file = StringField(required=True)
    map_file_dir = StringField(required=True)
    meta = {
        'indexes': [
            'map_file_id',
            'psap_id'
        ]
    }



