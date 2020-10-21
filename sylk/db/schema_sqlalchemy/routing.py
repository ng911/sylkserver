from .db import Base, getUniqueId
from .psap import Psap
from sqlalchemy import String, Column, ForeignKey, PickleType, DateTime, Integer, Boolean, Enum, CheckConstraint, UniqueConstraint
import enum
from sqlalchemy.orm import relationship
from .queue import Queue

class VoicePrompt(Base):
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False)
    description = Column(String)
    file_name = Column(PickleType)


class IVRChoice(enum.Enum):
    'Prompt Only' = 'Prompt Only'
    'Prompt with Key Press' = 'Prompt with Key Press'

class IVRCompletion(enum.Enum):
    'Hangup' =  'Hangup'
    'Go to ACD' = 'Go to ACD'

class IVR(Base):
    ivr_id = Column(String, primary_key=True)
    psap_id = Column(String, ForeignKey(Psap.psap_id))
    ivr_name = Column(String)
    use_key = Column(Integer)
    on_key = Column(Enum(IVRChoice))
    play_prompt = relationship('VoicePrompt')
    ivr_type = Column(Enum(IVRChoice))
    on_ivr_completion = Column(Enum(IVRCompletion))
    __table_args__ = (UniqueConstraint('ivr_id'))

class OrigType(enum.Enum):
    'sos_wireless' = 'sos_wireless'
    'sos_wireless' = 'sos_wireless'
    'admin' = 'admin'
    'sos_text' = 'sos_text'
    'calltaker_gateway' = 'calltaker_gateway'

class IncomingLink(Base):
    link_id = Column(String, primary_key=True, index=True,default=getUniqueId())
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False, index=True)
    name = Column(String)
    orig_type = Column(Enum(OrigType), nullable=False)
    max_channels = Column(Integer)
    ip_address = Column(String)
    regex = Column(Boolean, default=False) # called_number is matched with python regex
    port = Column(Integer)
    called_no = Column(String)
    ringback = Column(Boolean, default=False)
    queue_id = Column(String, ForeignKey(Queue.queue_id))
    ali_format = Column(String)
    use_called_number_for_ani = Column(Boolean, default=False, nullable=True)
    strip_ani_prefix = Column(Integer, default=0, nullable=True)
    strip_ani_suffix = Column(Integer, default=0, nullable=True)
    strip_from_prefix = Column(Integer, default=0, nullable=True)
    strip_from_suffix = Column(Integer, default=0, nullable=True)
    __table_args__ = (
        CheckConstraint('max_channels>=0', 'port>=0'), UniqueConstraint('link_id')
    )
    
    def is_origination_calltaker(self):
        return self.orig_type == 'calltaker_gateway'

    def is_origination_admin(self):
        return self.orig_type == 'admin'

    def is_origination_sos(self):
        return self.is_origination_sos_wireless() or self.is_origination_sos_wireline() or self.is_origination_sos_text()

    def is_origination_sos_wireless(self):
        return self.orig_type == 'sos_wireless'

    def is_origination_sos_wireline(self):
        return self.orig_type == 'sos_wireline'

    def is_origination_sos_text(self):
        return self.orig_type == 'sos_text'

def add_calltaker_gateway(ip_addr, psap_id):
    IncomingLink(psap_id=psap_id, name="calltaker gateway", orig_type='calltaker_gateway', ip_address=ip_addr).save()


class OutgoingLink(Base):
    link_id = Column(String, primary_key=True, index=True)
    ip_address = Column(String, nullable=False, index=True)
    port = Column(Integer)
    from_value = Column(String)
    __table_args__ = (CheckConstraint('port >= 0'))
   

# add this later
class DialPlan(Base):
    pass

class CallType(enum.Enum):
    'wireless' = 'wireless'
    'wireline' = 'wireline'

class CallTransferLine(Base):
    line_id = Column(String, primary_key=True, default=getUniqueId(), index=True)
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=True, index=True)
    type = Column(Enum(CallType), nullable=True, index=True)
    name = Column(String, nullable=False)
    star_code = Column(String, nullable=True)
    target = Column(String, nullable=True)
