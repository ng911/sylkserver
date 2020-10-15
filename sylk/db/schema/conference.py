import datetime, logging, traceback
import bson
from mongoengine import *

from .core import graphql_node_notifications

log = logging.getLogger("emergent-ng911")


class Call(Document):
    psap_id = ObjectIdField(required=True)
    call_id = ObjectIdField(required=True, default=bson.ObjectId)
    sip_call_id = StringField()
    from_uri = StringField()
    to_uri = StringField()
    direction = StringField(required=True, choices=('in', 'out'), default='in')
    start_time = ComplexDateTimeField(default=datetime.datetime.utcnow)
    answer_time = ComplexDateTimeField(required=False)
    end_time = ComplexDateTimeField(required=False)
    room_number = StringField(required=False)
    failure_code = StringField(required=False)
    failure_reason = StringField(required=False)
    status = StringField(required=True, choices=('init', 'reject', 'failed', 'ringing', 'queued', 'abandoned', 'active', 'closed', 'cancel'), default='init')
    meta = {
        'indexes': [
            'psap_id', 'call_id'
        ]
    }


class Agency(EmbeddedDocument):
    name = StringField()
    data = StringField()

@graphql_node_notifications
class Conference(Document):
    psap_id = ObjectIdField(required=True)
    room_number = StringField(required=True)
    incident_id = StringField(required=False)
    incident_details = StringField(required=False)
    start_time = ComplexDateTimeField(default=datetime.datetime.utcnow)
    answer_time = ComplexDateTimeField(required=False)
    end_time = ComplexDateTimeField(required=False)
    updated_at = ComplexDateTimeField(required=True, default=datetime.datetime.utcnow)
    has_text = BooleanField(default=False)
    has_tty = BooleanField(default=False)
    tty_text = StringField(required=False)
    has_audio = BooleanField(default=True)
    has_video = BooleanField(default=False)
    direction = StringField(required=True, choices=('in', 'out'), default='in')
    duration = IntField(default=0)
    type1 = StringField()   # not sure what this is, copied from old schema
    type2 = StringField()   # not sure what this is, copied from old schema
    pictures = ListField()
    call_type = StringField(required=True, choices=('normal', 'sos', 'admin', 'sos_text', 'outgoing', 'outgoing_calltaker'))
    partial_mute = BooleanField(default=False)
    hold = BooleanField(default=False)
    full_mute = BooleanField(default=False)
    # timed_out is for outgoing calls and abandoned is for incoming
    status = StringField(required=True, choices=('init', 'ringing', 'ringing_queued', 'queued', 'active', 'on_hold', 'closed', 'abandoned', 'timed_out', 'cancel', 'failed'))
    callback = BooleanField(default=False)
    callback_time = ComplexDateTimeField()
    callback_number = StringField()
    hold_start = ComplexDateTimeField()
    primary_queue_id = ObjectIdField()
    secondary_queue_id = ObjectIdField()
    link_id = ObjectIdField(required=False)
    #todo this should be moved to location?
    #agencies = EmbeddedDocumentListField(document_type=Agency)
    is_ani_pseudo = BooleanField(default=False)
    caller_ani = StringField()
    caller_uri = StringField()
    called_uri = StringField()      # called uri used by the original caller
    caller_name = StringField()
    recording =  StringField()
    note =  StringField()
    location_display = StringField()
    emergency_type = StringField(default='')
    secondary_type = StringField(default='')
    ali_result = StringField(default='none', hoices=('success', 'failed', 'pending', 'no records found', 'none', 'ali format not supported'))
    ali_format = StringField()
    ringing_calltakers = ListField()
    meta = {
        'indexes': [
            'psap_id',
            'room_number',
            'start_time',
            'call_type',
            'callback',
            'status'
        ]
    }


@graphql_node_notifications
class ConferenceParticipant(Document):
    psap_id = ObjectIdField()
    room_number = StringField(required=True)
    admin_line_id = ObjectIdField(required=False)
    sip_uri = StringField()
    name = StringField()
    is_caller = BooleanField(default=False)
    is_calltaker = BooleanField(default=False)
    is_primary = BooleanField(default=False)
    direction = StringField(required=True, choices=('in', 'out'), default='in')
    hold = BooleanField(default=False)
    mute = BooleanField(default=False)
    is_send = BooleanField(default=True)
    is_receive = BooleanField(default=True)
    is_active = BooleanField(default=True)
    has_text = BooleanField(default=False)
    has_audio = BooleanField(default=True)
    has_video = BooleanField(default=False)
    send_video = BooleanField(default=True)
    send_audio = BooleanField(default=True)
    send_text = BooleanField(default=True)
    meta = {
        'indexes': [
            'sip_uri',
            'room_number',
            'name'
        ]
    }


@graphql_node_notifications
class ConferenceEvent(Document):
    psap_id = ObjectIdField(required=True)
    room_number = StringField(required=True)
    event = StringField(required=True, choices=('join', 'leave', 'init', 'ringing', 'ringing_queued', \
                                                'queued', 'active', 'closed', 'start_hold', 'end_hold', 'mute', 'end_mute', \
                                                'abandoned', 'cancel', 'failed', 'update_primary', 'timed_out', 'enable_tty', \
                                                'transfer'))
    event_details = StringField()
    event_time = ComplexDateTimeField(default=datetime.datetime.utcnow)
    meta = {
        'indexes': [
            'event',
            'room_number'
        ]
    }

