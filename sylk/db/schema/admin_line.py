import datetime, logging, traceback
import bson
from mongoengine import *

from .core import graphql_node_notifications

log = logging.getLogger("emergent-ng911")


class AdminLineGroup(Document):
    psap_id = ObjectIdField(required=True)
    role_id = ObjectIdField()
    group_id = ObjectIdField(required=True, default=bson.ObjectId, unique=True)
    display_name = StringField(required=True)
    order = IntField()


class AdminLine(Document):
    psap_id = ObjectIdField(required=True)
    role_id = ObjectIdField()
    admin_line_id = ObjectIdField(required=True, default=bson.ObjectId, unique=True)
    server_id = ObjectIdField(required=False)
    icon_file = StringField()
    group_id = ObjectIdField()
    server = StringField()
    name = StringField(required=True)
    to_match = StringField()
    from_match = StringField()
    num_channnels = IntField()
    allow_outgoing = BooleanField(default=True)

