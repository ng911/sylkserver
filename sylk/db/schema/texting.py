import datetime, logging, traceback
import bson
from mongoengine import *

from .core import graphql_node_notifications

log = logging.getLogger("emergent-ng911")


@graphql_node_notifications
class ConferenceMessage(Document):
    psap_id = ObjectIdField(required=True)
    room_number = StringField(required=True)
    sender_uri = StringField()
    message = StringField()
    message_id = StringField()
    message_time = ComplexDateTimeField(default=datetime.datetime.utcnow)
    content_type = StringField()
    meta = {
        'indexes': [
            'sender_uri',
            'room_number'
        ]
    }



class Greeting(Document):
    greeting_id = ObjectIdField(required=True, default=bson.ObjectId)
    psap_id = ObjectIdField(required=True)
    user_id = ObjectIdField()
    desc = StringField(required=True)
    group = StringField()
    meta = {
        'indexes': [
            'psap_id',
            'greeting_id',
            'user_id'
        ]
    }

