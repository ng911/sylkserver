from datetime import datetime
import bcrypt

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, UniqueConstraint, \
    Sequence, Float,PrimaryKeyConstraint, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref

from .db import engine, getUniqueId, Base
from .psap import Psap


class User(Base):
    __tablename__ = "user"
    user_id = Column(String, primary_key=True, default=getUniqueId)
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False)
    status = Column(String, nullable=False, default='offline')
    username = Column(String, nullable=False, index=True)
    fullname = Column(String, nullable=True, index=False)
    password_hash = Column(String, nullable=False, index=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    is_active = Column(Boolean, default=True, nullable=False)
    is_available = Column(Boolean, default=False, nullable=False)
    extension = Column(String, nullable=True, index=True)
    station_id = Column(String, nullable=True, index=False)

    def check_password(self, password):
        password = password.encode('utf-8')
        password_hash = self.password_hash
        password_hash = password_hash.encode('utf-8')

        return bcrypt.checkpw(password, password_hash)

    @classmethod
    def generate_password_hash(cls, password):
        password = password.encode('utf-8')
        return bcrypt.hashpw(password, bcrypt.gensalt(10)).decode('utf-8')

'''
add these later
    group_id = ObjectIdField()
    roles = ListField(field=ObjectIdField())
    skillsets = ListField(field=ObjectIdField())
    layout = DictField(required=False)
'''


