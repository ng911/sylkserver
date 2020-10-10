from .psap import Psap
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean
from .db import Base
import bson


class AdminLineGroup(Base):
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False)
    group_id = Column(String, primary_key=True, nullable=False, unique=True)
    display_name = Column(String, nullable=False)
    order = Column(Integer)

class AdminLine(Base):
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False)
    admin_line_id = Column(String,)
    group_id = Column(String, primary_key=True, nullable=False, unique=True)
    server = Column(String)
    name = Column(String, nullable=False)
    to_match = Column(String)
    from_match = Column(String)
    num_channnels = Column(Integer)
    allow_outgoing = Column(Boolean)