from .psap import Psap
from .user import User
from .db import Base, getUniqueId

from sqlalchemy import Column, String, ForeignKey, Boolean, PickleType, UniqueConstraint
from sqlalchemy.orm import relationship

class SpeedDialGroup(Base):
    group_id = Column(String, primary_key=True, default=getUniqueId())
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False, index=True)
    role_id = Column(String)
    user_id = Column(String, ForeignKey(User.user_id))
    group_name = Column(String, nullable=False, index=True)
    __table_args__ = (UniqueConstraint('group_id'))


class SpeedDial(Base):
    speed_dial_id = Column(String, primary_key=True, default=getUniqueId())
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False, index=True)
    role_id = Column(String)
    user_group_id = Column(String)
    user_id = Column(String, ForeignKey(User.user_id), index=True)
    dest = Column(String, nullable=False)
    name = Column(String, nullable=False)
    group_id = Column(String, index=True)
    group = relationship('SpeedDialGroup', backref="speeddial")
    show_as_button = Column(Boolean)
    icon = Column(String)
    files = Column(PickleType)
    __table_args__ = (UniqueConstraint('speed_dial_id'))