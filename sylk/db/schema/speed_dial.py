import logging
import bson
from mongoengine import *
from .core import graphql_node_notifications


log = logging.getLogger("emergent-ng911")


@graphql_node_notifications
class SpeedDialGroup(Document):
    group_id = ObjectIdField(required=True, default=bson.ObjectId, unique=True)
    psap_id = ObjectIdField(required=True)
    user_id = ObjectIdField()
    group_name = StringField(required=True)
    meta = {
        'indexes': [
            'psap_id',
            'group_name',
            {
                'fields': ['psap_id', 'group_name'],
                'unique': True
            }
        ]
    }


@graphql_node_notifications
class SpeedDial(Document):
    speed_dial_id = ObjectIdField(required=True, default=bson.ObjectId, unique=True)
    psap_id = ObjectIdField()
    user_group_id = ObjectIdField()
    user_id = ObjectIdField()
    dest = StringField(required=True)
    name = StringField(required=True)
    group_id = ObjectIdField()
    group = LazyReferenceField(document_type=SpeedDialGroup)
    show_as_button = BooleanField()
    icon = StringField()
    files = ListField(StringField())
    meta = {
        'indexes': [
            'psap_id',
            'user_id',
            'group_id',
            {
                'fields': ['psap_id', 'name', "group_id", "user_id"],
                'unique': True
            }
        ]
    }

