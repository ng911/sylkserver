from datetime import datetime
import bcrypt
import enum

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, UniqueConstraint, \
    Sequence, Float, PrimaryKeyConstraint, ForeignKey, ARRAY, PickleType, Enum, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref

from .db import engine, getUniqueId, Base
from .psap import Psap


class Role(Base):
    name = Column(String, index=True)
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False, index=True)

class UserGroup(Base):
    name = Column(String, index=True)
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False, index=True)
    permissions = Column(PickleType)

class SkillSet(Base):
    name = Column(String)
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False)
    __table_args__ = (UniqueConstraint('name'))

class UserPermission(Base):
    name = Column(String, index=True)
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False, index=True)
    __table_args__ = (UniqueConstraint('name'))

    @classmethod
    def create_permissions(cls):
        permissions = ["Answer 911 calls", "Monitor 911 Calls", "Barge In", \
                       "Admin Lines", \
                       "Create PSAPs", "PSAP Admin", \
                       "Create Users", "PSAP Routing", \
                       "Access Reports"
                       ]
        for permission in permissions:
            try:
                userPermission = UserPermission.query.filter(name=permission)
            except DoesNotExist:
                userPermission = UserPermission()
                userPermission.name = permission
                userPermission.save()


class User(Base):
    __tablename__ = "user"
    user_id = Column(String, primary_key=True, default=getUniqueId(), index=True)
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False, index=True)
    secondary_psap_id = Column(String, ForeignKey(Psap.psap_id))
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
    roles = Column(ARRAY(Role))
    skillsets = Column(ARRAY(SkillSet))
    layout = Column(PickleType)
    __table_args__ = (UniqueConstraint('user_id', 'username', 'password_hash'))

    def check_password(self, password):
        password = password.encode('utf-8')
        password_hash = self.password_hash
        password_hash = password_hash.encode('utf-8')

        return bcrypt.checkpw(password, password_hash)

    @classmethod
    def generate_password_hash(cls, password):
        password = password.encode('utf-8')
        return bcrypt.hashpw(password, bcrypt.gensalt(10)).decode('utf-8')

    @classmethod
    def add_user(cls, username, password):
        user = User()
        user.username = username
        #if isinstance(password, unicode):
        # py3 compatible replacement below
        if isinstance(password, six.text_type):
            password = password.encode('ascii')
        user.password_hash = User.generate_password_hash(password)
        user.is_active = True
        user.roles = ['admin', 'calltaker']
        log.info("user.password_hash is %r", user.password_hash)
        user.save()
        return  user

    @classmethod
    def add_user_psap(cls, username, password, psap_id):
        user = User()
        user.psap_id = psap_id
        user.username = username
        #if isinstance(password, unicode):
        # py3 compatible replacement below
        user.password_hash = User.generate_password_hash(password)
        user.is_active = True
        user.roles = ['admin', 'calltaker']
        log.info("user.password_hash is %r", user.password_hash)
        user.save()
        return  user
'''
add these later
    group_id = ObjectIdField()
    roles = ListField(field=ObjectIdField())
    skillsets = ListField(field=ObjectIdField())
    layout = DictField(required=False)
'''

class CalltakerStation(Base):
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False)
    station_id = Column(String, nullable=False, index=True)
    ip_address = Column(String, nullable=False)
    name = Column(String, nullable=False, index=True)
    loud_ring_server = Column(Boolean)
    __table_args__ = (UniqueConstraint('name', 'station_id', 'ip_address'))


class CalltakerProfile(Base):
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False)
    profile_id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(User.user_id), nullable=True, index=True)
    incoming_ring = Column(Boolean, default=True)
    ringing_server_volume = Column(Integer, default=50)
    incoming_ring_level = Column(Integer, default=50)
    ring_delay = Column(Integer, default=0)
    auto_respond = Column(Boolean, default=False)
    auto_respond_after = Column(Integer, default=10)
    __table_args__ = (CheckConstraint (
            '0<=ringing_server_volume', 'ringing_server_volume<=100', 
            '0<=incoming_ring_level', 'incoming_ring_level<=100', 'ring_delay>=0', 'auto_respond_after>=0'
            )
        )

    @classmethod
    def get_default_profile(cls):
        return {
            "incoming_ring" : True,
            "ringing_server_volume" : 50,
            "incoming_ring_level" : 50,
            "ring_delay" : 0,
            "auto_respond" : False,
            "auto_respond_after" : 10
        }


class Event(enum.Enum):
    'login' = 'login'
    'made_busy' = 'made_busy'
    'dial_out' = 'dial_out'
    'join_call' = 'join_call'
    'answer_call' = 'answer_call'
    'hang_up' = 'hang_up'
    'logout' = 'logout'
    'rebid' = 'rebid'

class CalltakerActivity(Document):
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False)
    user_id = Column(Integer, ForeignKey(User.user_id), nullable=False, index=True)
    event = Column(Enum(Event), nullable=False, index=True)
    event_details = Column(String)
    event_num_data = Column(Float)
    start_time = Column(DateTime, default=datetime.datetime.utcnow(), index=True)
    #end_time = ComplexDateTimeField(default=datetime.datetime.utcnow)
    