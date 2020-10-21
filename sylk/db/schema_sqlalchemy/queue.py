from .psap import Psap
from .user import User
from sqlalchemy import Column, String, ForeignKey, Enum, Integer, UniqueConstraint, CheckConstraint
import enum
from .db import Base, getUniqueId

class Acd(enum.Enum):
    'ring_all' = 'ring'
    'most_idle' = 'most_idle'
    'round_robin' = 'round_robin'
    'random' =  'random'

class Queue(Base):
    queue_id = Column(String, primary_key=True, index=True default=getUniqueId())
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False, index=True)
    acd_strategy = Column(Enum(Acd), default='ring_all', nullable=False)
    name = Column(String, default='default', nullable=False, unique=True)
    ring_time = Column(Integer, default=30, nullable=False)
    rollover_queue_id = Column(String, nullable=True)
    __table_args__ = (UniqueConstraint('queue_id'), CheckConstraint('ring_time>=0'))


class QueueMember(Base):
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False)
    user_id = Column(String, ForeignKey(User.user_id), nullable=False, index=True)
    queue_id = Column(String, ForeignKey(Queue.queue_id), nullable=False, index=True)