from .psap import Psap
from sqlalchemy import Column, String, Integer, ForeignKey, Enum, CheckConstraint, DateTime, Float, Boolean, PickleType
from .db import Base
import enum
from datetime import datetime

class Location(Base):
    psap_id = Column(String, ForeignKey(Psap.psap_id))
    room_number = Column(String, nullable=False)
    location_id = Column(String, nullable=False)
    time = Column(DateTime, default=datetime.utcnow())
    updated_at = Column(DateTime, default=datetime.utcnow())
    ali_format = Column(String)
    raw_format =  Column(String)
    phone_number =  Column(String)
    category =  Column(String)
    name =  Column(String)
    alternate =  Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    radius = Column(Float)
    location_point = Column(PickleType)
    callback =  Column(String)
    state =  Column(String)
    contact =  Column(String)
    location =  Column(String)
    service_provider =  Column(String)
    contact_display =  Column(String)
    community =  Column(String)
    secondary =  Column(String)
    class_of_service =  Column(String)
    agencies_display =  Column(String)
    fire_no =  Column(String)
    ems_no =  Column(String)
    police_no =  Column(String)
    otcfield =  Column(String)
    psap_no =  Column(String)
    esn =  Column(String)
    postal =  Column(String)
    psap_name =  Column(String)
    pilot_no =  Column(String)
    descrepancy = Column(Boolean, default=False)

class ServerType(enum.Enum):
    'wireless' =  'wireless'
    'wireline' = 'wireline'

class AliServer(Base):
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False)
    type = Column(Enum(ServerType))
    format = Column(String)
    ip1 = Column(String)
    port1 = Column(Integer)
    ip2 = Column(String)
    port2 = Column(Integer)
    name = Column(String)
    __table_args__ = (
        CheckConstraint(port1 >= 0), CheckConstraint(port2 >= 0)
    )