import datetime, logging
import bson
import bcrypt
import six
from mongoengine import *
from .core import graphql_node_notifications


# from werkzeug.security import generate_password_hash, check_password_hash
log = logging.getLogger("emergent-ng911")


class UserRole(Document):
    name = StringField()
    psap_id = ObjectIdField()


class UserGroup(Document):
    name = StringField()
    psap_id = ObjectIdField()
    permissions = ListField(field=ObjectIdField())


class UserPermission(Document):
    name = StringField()
    psap_id = ObjectIdField()


@graphql_node_notifications
class User(Document):
    user_id = ObjectIdField(required=True, unique=True, default=bson.ObjectId)
    status = StringField(required=True, default='offline')
    username = StringField(required=True, unique=True)
    fullname = StringField(required=False)
    password_hash = StringField(required=True, unique=True)
    created_at = ComplexDateTimeField(required=True, default=datetime.datetime.utcnow)
    psap_id = ObjectIdField()
    secondary_psap_id = ObjectIdField()
    is_active = BooleanField(default=True)
    is_available = BooleanField(default=False)
    extension = StringField()
    station_id = StringField(required=False)
    group_id = ObjectIdField()
    roles=ListField(field=ObjectIdField())
    layout = DictField(required=False)
    meta = {
        'indexes': [
            'user_id',
            'username',
            'psap_id',
            'group_id'
        ]
    }

    def get_id(self):
        return str(self.user_id)

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


@graphql_node_notifications
class CalltakerStation(Document):
    psap_id = ObjectIdField(required=True)
    station_id = StringField(required=True, unique=True)
    ip_address = StringField(required=True, unique=True)
    name = StringField(required=True, unique=True)
    loud_ring_server = BooleanField()
    meta = {
        'indexes': [
            'station_id',
            'name'
        ]
    }


@graphql_node_notifications
class CalltakerProfile(DynamicDocument):
    psap_id = ObjectIdField(required=True)
    profile_id = ObjectIdField(required=True, unique=True, default=bson.ObjectId)
    user_id = ObjectIdField(required=False)
    incoming_ring = BooleanField(default=True)
    ringing_server_volume = IntField(min_value=0, max_value=100, default=50)
    incoming_ring_level = IntField(min_value=0, max_value=100, default=50)
    ring_delay = IntField(min_value=0, default=0)
    auto_respond = BooleanField(default=False)
    auto_respond_after = IntField(min_value=0, default=10)
    meta = {
        'indexes': [
            'profile_id',
            'user_id'
        ]
    }

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


@graphql_node_notifications
class CalltakerActivity(Document):
    psap_id = ObjectIdField(required=True)
    user_id = ObjectIdField(required=True)
    event = StringField(required=True, choices=('login', 'made_busy', 'dial_out', 'join_call', 'answer_call', 'hang_up', 'logout', 'rebid'))
    event_details = StringField()
    event_num_data = FloatField()
    start_time = ComplexDateTimeField(default=datetime.datetime.utcnow)
    #end_time = ComplexDateTimeField(default=datetime.datetime.utcnow)
    meta = {
        'indexes': [
            'user_id',
            'event',
            'start_time'
        ]
    }


