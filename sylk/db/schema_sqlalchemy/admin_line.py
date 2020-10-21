from .psap import Psap
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, UniqueConstraint
from .db import Base, getUniqueId
import bson


class AdminLineGroup(Base):
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False)
    group_id = Column(String, primary_key=True, default=getUniqueId(), nullable=False)
    display_name = Column(String, nullable=False)
    order = Column(Integer)
    __table_args__ = (UniqueConstraint('group_id'))

class AdminLine(Base):
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False)
    admin_line_id = Column(String, primary_key=True, default=getUniqueId(), nullable=False)
    group_id = Column(String, ForeignKey(AdminLineGroup.group_id))
    server = Column(String)
    name = Column(String, nullable=False)
    to_match = Column(String)
    from_match = Column(String)
    num_channnels = Column(Integer)
    allow_outgoing = Column(Boolean)
    __table_args__ = (UniqueConstraint('admin_line_id'))