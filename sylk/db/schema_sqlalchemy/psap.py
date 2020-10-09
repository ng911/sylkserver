from datetime import datetime
from .db import engine, getUniqueId, Base
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, UniqueConstraint, \
    Sequence, Float,PrimaryKeyConstraint, ForeignKey, Enum
import enum

class Acd_Choice(enum.Enum):
    'ring_all' = 'Ring All'
    'least_idle' ='Least Idle'
    'random' = 'Random'

class Call_Handling_Choice(enum.Enum):
    'acd' = 'ACD'
    'defined_ivrs' = 'Define IVRs'
    'defined_geo_routes' = 'Defined Geo Routes'

class Psap(Base):
    __tablename__ = "psap"
    psap_id = Column(String, primary_key=True, default=getUniqueId)
    psap_name = Column(String, nullable=False, index=True)
    domain_name = Column(String, nullable=False, index=True)
    time_to_autorebid = Column(Integer, default=30)
    auto_rebid = Column(Boolean, default=True)
    max_calls_in_queue = Column(Integer, default=4)
    default_user_profile_id = Column(String)
    time_created = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String)
    domain_name_prefix = Column(String)
    cad_listen_port = Column(Integer)
    auto_rebid_time = Column(Integer)
    sos_call_handling = Column(Enum(Call_Handling_Choice))
    sos_acd = Column(Enum(Acd_Choice))
    enable_overflow_handling = Column(Boolean, default=True)
    overflow_uri = Column(String)
    __table_args__ = (UniqueConstraint('domain_name', name='_psap_domain_name'), )