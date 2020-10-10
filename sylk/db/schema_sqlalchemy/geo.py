from .psap import Psap
from .routing import IVR
from .db import Base

from sqlalchemy import Column, String, PickleType, ForeignKey
from sqlalchemy.orm import relationship


class GeoRouting(Base):
    georouting_id = Column(String, primary_key=True)
    psap_id = Column(String, ForeignKey(Psap.psap_id))
    description = Column(String)
    file_name = Column(PickleType)
    routing = relationship('IVR')