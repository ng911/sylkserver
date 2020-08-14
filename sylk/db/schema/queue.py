import logging
import bson
from mongoengine import *

from .core import graphql_node_notifications

# from werkzeug.security import generate_password_hash, check_password_hash
log = logging.getLogger("emergent-ng911")

@graphql_node_notifications
class Queue(Document):
    queue_id = ObjectIdField(required=True, default=bson.ObjectId, unique=True)
    psap_id = ObjectIdField(required=True)
    acd_strategy = StringField(required=True, default='ring_all', choices=('ring_all', 'most_idle', 'round_robin', 'random') )
    name = StringField(required=True, default='default', unique=True)        #default is default queue
    ring_time = IntField(min_value=0, default=30, required=True)
    rollover_queue_id = ObjectIdField(required=False, default=None)
    meta = {
        'indexes': [
            'queue_id',
            'psap_id'
        ]
    }


@graphql_node_notifications
class QueueMember(Document):
    psap_id = ObjectIdField(required=True)
    user_id = ObjectIdField(required=True)
    queue_id = ObjectIdField(required=True)
    meta = {
        'indexes': [
            {
                'fields' : ['queue_id', 'user_id'],
                'unique' : True
            }
        ]
    }

