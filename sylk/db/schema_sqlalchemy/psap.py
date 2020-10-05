from datetime import datetime
from .db import engine, getUniqueId, Base
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, UniqueConstraint, \
    Sequence, Float,PrimaryKeyConstraint, ForeignKey


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
    __table_args__ = (UniqueConstraint('domain_name', name='_psap_domain_name'), )





