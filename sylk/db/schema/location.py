import logging
import datetime
import bson
from mongoengine import *
from .core import graphql_node_notifications

log = logging.getLogger("emergent-ng911")


@graphql_node_notifications
class Location(Document):
    psap_id = ObjectIdField(required=True)
    room_number = StringField(required=True)
    location_id = ObjectIdField(required=True, default=bson.ObjectId)
    time = ComplexDateTimeField(default=datetime.datetime.utcnow)
    updated_at = ComplexDateTimeField(default=datetime.datetime.utcnow)
    ali_format = StringField()
    raw_format = StringField()
    phone_number = StringField()
    category = StringField()
    name = StringField()
    alternate = StringField()
    latitude = FloatField()
    longitude = FloatField()
    radius = FloatField()
    location_point = PointField()
    callback = StringField()
    state = StringField()
    contact = StringField()
    location = StringField()
    service_provider = StringField()
    contact_display = StringField()
    community = StringField()
    secondary = StringField()
    class_of_service = StringField()
    agencies_display = StringField()
    fire_no = StringField()
    ems_no = StringField()
    police_no = StringField()
    otcfield = StringField()
    psap_no = StringField()
    esn = StringField()
    postal = StringField()
    psap_name = StringField()
    pilot_no = StringField()
    descrepancy = BooleanField(default=False)
    meta = {
        'indexes': [
            'room_number',
            'location_id'
        ]
    }
    '''
    "caller" : {
        "category" : "unknown",
        "agenciesDisplay" : "OTC1122           TEL=QWST",
        "name" : "Mark Twain",
        "callId" : "4e3451d74af1656b09ef633d0e4fac1a@54.243.134.79:5060",
        "alternate" : null,
        "longitude" : "",
        "callback" : "4155551212",
        "state" : "CA",
        "contact" : "<sip:4153054541@54.243.134.79>",
        "radius" : "",
        "location" : "1233 E North Point Street Apt 403",
        "provider" : "",
        "latitude" : "",
        "contactDisplay" : "4155551212",
        "community" : "San Francisco",
        "secondary" : "",
        "pAni" : "4155551212",
        "cls" : "WPH1"
    },
    '''


class AliServer(Document):
    psap_id = ObjectIdField(required=True)
    type = StringField(required=True, choices=('wireless', 'wireline'))
    format = StringField()
    ip1  = StringField()
    port1 = IntField(min_value=0)
    ip2 = StringField()
    port2 = IntField(min_value=0)
    name = StringField()
    meta = {
        'indexes': [
            'psap_id',
            'type',
            'format'
        ]
    }

