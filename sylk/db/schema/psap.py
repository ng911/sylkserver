import logging
import bson
from mongoengine import *

from .core import graphql_node_notifications

# from werkzeug.security import generate_password_hash, check_password_hash
log = logging.getLogger("emergent-ng911")

@graphql_node_notifications
class Psap(Document):
    acd_choice = (
        ('ring_all', 'Ring All'), ('least_idle','Least Idle'), ('random', 'Random')
    )
    call_handling_choice = (
        ('acd','ACD'), ('defined_ivrs', 'Define IVRs'), ('defined_geo_routes','Defined Geo Routes')
    )
    psap_id = ObjectIdField(required=True, default=bson.ObjectId, unique=True)
    name = StringField()
    time_to_autorebid = IntField(default=30)
    domain = StringField()
    ip_address = StringField()
    auto_rebid = BooleanField(default=True)
    default_profile_id = ObjectIdField()
    domain_name_prefix = StringField()
    cad_listen_port = IntField()
    auto_rebid_time = IntField()
    sos_call_handling = StringField(choices=call_handling_choice)
    sos_acd = StringField(choices=acd_choice)
    enable_overflow_handling = BooleanField(default=True)
    max_calls_in_queue = IntField()
    overflow_uri = StringField()
    meta = {
        'indexes': [
            'psap_id', 'name', 'domain'
        ]
    }

