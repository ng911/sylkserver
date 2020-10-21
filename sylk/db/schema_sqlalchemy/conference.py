from .db import Base, getUniqueId
from .psap import Psap
from sqlalchemy import String, Column, ForeignKey, PickleType, DateTime, Enum, Boolean, Integer
import enum
import datetime
from .queue import Queue

class CallDirection(enum.Enum):
    'in' = 'in'
    'out' = 'out'

class CallStatus(enum.Enum):
    'init'= 'init'
    'reject'= 'reject'
    'failed'= 'failed'
    'ringing'= 'ringing'
    'queued'= 'queued'
    'abandoned'= 'abandoned'
    'active'= 'active'
    'closed'= ' closed'
    'cancel' = 'cancel'

class Call(Base):
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False, index=True)
    call_id = Column(String, primary_key=True, default=getUniqueId(), index=True)
    sip_call_id = Column(String)
    from_uri = Column(String)
    to_uri = Column(String)
    direction = Column(Enum(CallDirection), nullable=False,  default='in')
    start_time = Column(DateTime,default=datetime.datetime.utcnow())
    answer_time = Column(DateTime,nullable=True)
    end_time = Column(DateTime,nullable=True)
    room_number = Column(String, nullable=True)
    failure_code = Column(String, nullable=True)
    failure_reason = Column(String, nullable=True)
    status = Column(Enum(CallStatus), nullable=False, default='init')


class Agency(Base):
    name = Column(String)
    data = Column(String)

class AliResult(enum.Enum):
    'success' = 'success' 
    'failed' = 'failed'
    'pending' = 'pending'
    'no records found' = 'no records found'
    'none' = 'none'
    'ali format not supported' = 'ali format not supported' 

class CallType(enum.Enum):
    'normal' = 'normal'
    'sos' = 'sos'
    'admin' = 'admin'
    'sos_text' = 'sos_text'
    'outgoing' = 'ongoing'
    'outgoing_calltaker' = 'outgoing_calltaker' 

class Conference(Base):
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False, index=True)
    room_number = Column(String, nullable=False, index=True)
    incident_id = Column(String, nullable=True)
    incident_details = Column(String, nullable=True)
    start_time = Column(DateTime, default=datetime.datetime.utcnow(), index=True)
    answer_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow())
    has_text = Column(Boolean, default=False)
    has_tty = Column(Boolean, default=False)
    tty_text = Column(String, nullable=True)
    has_audio = Column(Boolean, default=True)
    has_video = Column(Boolean, default=False)
    direction = Column(Enum(CallDirection), nullable=False, default='in')
    duration = Column(Integer, default=0)
    type1 = Column(String)   # not sure what this is, copied from old schema
    type2 = Column(String)   # not sure what this is, copied from old schema
    pictures = Column(PickleType)
    call_type = Column(Enum(CallType), nullable=False, index=True)
    partial_mute = Column(Boolean, default=False)
    hold = Column(Boolean, default=False)
    full_mute = Column(Boolean, default=False)
    # timed_out is for outgoing calls and abandoned is for incoming
    status = Column(Enum(CallStatus), nullable=False, index=True)
    callback = Column(Boolean, default=False)
    callback_time = Column(DateTime, default=datetime.datetime.utcnow())
    callback_number = Column(String)
    hold_start = Column(DateTime, default=datetime.datetime.utcnow())
    primary_queue_id = Column(String, ForeignKey(Queue.queue_id))
    secondary_queue_id = Column(String, ForeignKey(Queue.queue_id))
    link_id = Column(String, nullable=True)
    #todo this should be moved to location?
    #agencies = EmbeddedBaclass Conference(BaseListField(Baclass Conference(Base_type=Agency)
    is_ani_pseudo = Column(Boolean, default=False)
    caller_ani = Column(String)
    caller_uri = Column(String)
    called_uri = Column(String)      # called uri used by the original caller
    caller_name = Column(String)
    recording =  Column(String)
    note =  Column(String)
    location_display = Column(String)
    emergency_type = Column(String, default='')
    secondary_type = Column(String, default='')
    ali_result = Column(Enum(AliResult), default='none')
    ali_format = Column(String)
    ringing_calltakers = Column(PickleType)



class ConferenceParticipant(Base):
    psap_id = Column(String, ForeignKey(Psap.psap_id))
    room_number = Column(String, nullable=False, index=True)
    sip_uri = Column(String, index=True)
    name = Column(String, index=True)
    is_caller = Column(Boolean, default=False)
    is_calltaker = Column(Boolean, default=False)
    is_primary = Column(Boolean, default=False)
    direction = Column(Enum(CallDirection), nullable=False, default='in')
    hold = Column(Boolean, default=False)
    mute = Column(Boolean, default=False)
    is_send = Column(Boolean, default=True)
    is_receive = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    has_text = Column(Boolean, default=False)
    has_audio = Column(Boolean, default=True)
    has_video = Column(Boolean, default=False)
    send_video = Column(Boolean, default=True)
    send_audio = Column(Boolean, default=True)
    send_text = Column(Boolean, default=True)
    

class ConfEvent(enum.Enum):
    'join'= 'join'
    'leave'= 'leave'
    'init'= 'init'
    'ringing'= 'ringing'
    'ringing_queued'= 'ringing_queued'
    'queued'= 'queued'
    'active'= 'active'
    'closed'= 'closed'
    'start_hold'= 'start_hold'
    'end_hold'= 'end_hold'
    'mute'= 'mute'
    'end_mute' = 'end_mute'
    'abandoned' = 'abandoned'
    'cancel' = 'cancel'
    'failed' = 'failed'
    'update_primary' = 'update_primary'
    'timed_out' = 'timed_out'
    'enable_tty' = 'enable_tty'
    'transfer' = 'transfer'

class ConferenceEvent(Base):
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False)
    room_number = Column(String, nullable=False, index=True)
    event = Column(Enum(ConfEvent), nullable=False, index=True)
    event_details = Column(String)
    event_time = Column(DateTime,default=datetime.datetime.utcnow())