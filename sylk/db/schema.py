import arrow
import bson
import bcrypt
import datetime
from mongoengine import *
import time, datetime, logging, re, sys, traceback
# from werkzeug.security import generate_password_hash, check_password_hash
from collections import namedtuple

from sylk.applications import ApplicationLogger

log = ApplicationLogger(__package__)

def getIsoFormat(dateTimeObj):
    arrowDateTimeObj = arrow.get(dateTimeObj)
    return arrowDateTimeObj.format("YYYY-MM-DDTHH:mm:ss.SSSZ")


# this has higher precision for sub seconds
def getIsoMaxFormat(dateTimeObj):
    arrowDateTimeObj = arrow.get(dateTimeObj)
    return arrowDateTimeObj.format("YYYY-MM-DDTHH:mm:ss.SSSSSSZ")


#client = connect(username="ws", password="Ecomm@911",
#                 host='mongodb://ds133903-a1.mlab.com:33903/supportgenie_ws?replicaSet=rs-ds133903')
'''
client = connect(username="ws", password="Ecomm@911",
                 host='mongodb://localhost:33903/psap?replicaSet=rs-psap')
'''
#client = connect(host='mongodb://localhost:27107/ng911')
connect('ng911')
#db = client.ng911
#db.authenticate("ws", "Ecomm@911")



class Psap(Document):
    psap_id = ObjectIdField(required=True, default=bson.ObjectId, unique=True)
    name = StringField()
    time_to_autorebid = IntField(default=30)
    ip_address = StringField(default="127.0.0.1")
    auto_rebid = BooleanField(default=True)
    default_profile_id = ObjectIdField()


class User(Document):
    user_id = ObjectIdField(required=True, unique=True, default=bson.ObjectId)
    username = StringField(required=True, unique=True)
    password_hash = StringField(required=True, unique=True)
    created_at = ComplexDateTimeField(required=True, default=datetime.datetime.utcnow)
    psap_id = ObjectIdField()
    secondary_psap_id = ObjectIdField()
    is_active = BooleanField(default=True)
    roles=ListField(field=StringField(choices=('admin', 'calltaker', 'supervisor')))

    def get_id(self):
        return str(self.user_id)

    def check_password(self, password):
        if isinstance(password, unicode):
            password = password.encode('ascii')
        password_hash = self.password_hash

        if isinstance(password_hash, unicode):
            password_hash = password_hash.encode('ascii')

        return bcrypt.checkpw(password, password_hash)

    @classmethod
    def generate_password_hash(cls, password):
        if isinstance(password, unicode):
            password = password.encode('ascii')
        return bcrypt.hashpw(password, bcrypt.gensalt(10))

    @classmethod
    def add_user(cls, username, password):
        user = User()
        user.username = username
        if isinstance(password, unicode):
            password = password.encode('ascii')
        user.password_hash = User.generate_password_hash(password)
        user.is_active = True
        user.roles = ['admin', 'calltaker']
        user.save()
        return  user


class CallTakerStation(Document):
    station_id = StringField(required=True, unique=True, default=bson.ObjectId)
    name = StringField(required=True, unique=True)
    loud_ring_server = BooleanField()


class CallTakerProfile(DynamicDocument):
    profile_id = ObjectIdField(required=True, unique=True, default=bson.ObjectId)
    user_id = ObjectIdField(required=False)
    incoming_ring = BooleanField(default=True)
    ringing_server_volume = IntField(min_value=0, max_value=100, default=50)
    incoming_ring_level = IntField(min_value=0, max_value=100, default=50)
    ring_delay = IntField(min_value=0, default=0)
    auto_respond = BooleanField(default=False)
    auto_respond_after = IntField(min_value=0, default=10)


class CallTakerActivity(Document):
    user_id = ObjectIdField(required=True)
    event = StringField(required=True, choices=('login', 'made_busy', 'answer_call', 'hang_up', 'logout', 'rebid'))
    event_details = StringField()
    star_time = ComplexDateTimeField(default=datetime.datetime.utcnow)
    end_time = ComplexDateTimeField(default=datetime.datetime.utcnow)


class SpeedDial(Document):
    psap_id = ObjectIdField()
    user_id = ObjectIdField()
    dest = StringField(required=True)
    name = StringField(required=True)
    group = StringField(required=False)


class IncomingLink(Document):
    link_id = ObjectIdField(required=True, default=bson.ObjectId, unique=True)
    psap_id = ObjectIdField(required=True)
    name = StringField()
    orig_type = StringField(required=True, choices=('sos_wireless', 'sos_wireline', 'admin', 'sos_text', 'calltaker_gateway'))
    max_channels = IntField(min_value=0)
    ip_address = StringField()
    regex = BooleanField(default=False) # called_number is matched with python regex
    port = IntField(min_value=0)
    called_no = StringField()
    ringback = BooleanField(default=False)
    queue_id = ObjectIdField()
    ali_format = StringField()

    def is_origination_calltaker(self):
        return self.orig_type == 'calltaker_gateway'

    def is_origination_admin(self):
        return self.orig_type == 'admin'

    def is_origination_sos(self):
        return self.is_origination_sos_wireless() or self.is_origination_sos_wireline() or self.is_origination_sos_text()

    def is_origination_sos_wireless(self):
        return self.orig_type == 'sos_wireless'

    def is_origination_sos_wireline(self):
        return self.orig_type == 'sos_wireline'

    def is_origination_sos_text(self):
        return self.orig_type == 'sos_text'


class OutgoingLink(Document):
    link_id = ObjectIdField(required=True)
    ip_address = StringField(required=True)
    port = IntField(min_value=0)
    from_value = StringField()


# add this later
class DialPlan(Document):
    pass


class Queue(Document):
    queue_id = ObjectIdField(required=True, default=bson.ObjectId, unique=True)
    psap_id = ObjectIdField(required=True)
    acd_strategy = StringField(required=True, default='ring_all', choices=('ring_all', 'most_idle', 'round_robin', 'random') )
    name = StringField(required=True, default='default', unique=True)        #default is default queue
    ring_time = IntField(min_value=0, default=30, required=True)
    rollover_queue_id = ObjectIdField(required=False, default=None)


class QueueMember(Document):
    user_id = ObjectIdField(required=True)
    queue_id = ObjectIdField(required=True)


class Call(Document):
    psap_id = ObjectIdField(required=True)
    call_id = ObjectIdField(required=True, default=bson.ObjectId)
    sip_call_id = StringField()
    from_uri = StringField()
    to_uri = StringField()
    direction = StringField(required=True, choices=('in', 'out'), default='in')
    start_time = ComplexDateTimeField(default=datetime.datetime.utcnow)
    answer_time = ComplexDateTimeField(required=False)
    end_time = ComplexDateTimeField(required=False)
    room_number = StringField(required=False)
    failure_code = StringField(required=False)
    failure_reason = StringField(required=False)
    status = StringField(required=True, choices=('init', 'reject', 'failed', 'ringing', 'queued', 'abandoned', 'active', 'closed', 'cancel'), default='init')


class Agency(EmbeddedDocument):
    name = StringField()
    data = StringField()


class Conference(Document):
    psap_id = ObjectIdField(required=True)
    room_number = StringField(required=True)
    start_time = ComplexDateTimeField(default=datetime.datetime.utcnow)
    answer_time = ComplexDateTimeField(required=False)
    end_time = ComplexDateTimeField(required=False)
    updated_at = ComplexDateTimeField(required=True, default=datetime.datetime.utcnow)
    has_text = BooleanField(default=False)
    has_tty = BooleanField(default=False)
    has_audio = BooleanField(default=True)
    has_video = BooleanField(default=False)
    direction = StringField(required=True, choices=('in', 'out'), default='in')
    duration = IntField(default=0)
    type1 = StringField()   # not sure what this is, copied from old schema
    type2 = StringField()   # not sure what this is, copied from old schema
    pictures = ListField(field=StringField)
    call_type = StringField(required=True, choices=('normal', 'sos', 'admin', 'sos_text'))
    partial_mute = BooleanField(default=False)
    hold = BooleanField(default=False)
    full_mute = BooleanField(default=False)
    status = StringField(required=True, choices=('init', 'ringing', 'ringing_queued', 'queued', 'active', 'closed', 'abandoned', 'cancel'))
    callback = BooleanField(default=False)
    callback_time = ComplexDateTimeField()
    callback_number = StringField()
    hold_start = ComplexDateTimeField()
    primary_queue_id = ObjectIdField()
    secondary_queue_id = ObjectIdField()
    link_id = ObjectIdField(required=True)
    #todo this should be moved to location?
    #agencies = EmbeddedDocumentListField(document_type=Agency)
    caller_ani = StringField()
    caller_uri = StringField()
    caller_name = StringField()
    recording =  StringField()
    note =  StringField()
    emergency_type = StringField(default='')
    secondary_type = StringField(default='')

class ConferenceParticipant(Document):
    room_number = StringField(required=True)
    sip_uri = StringField()
    name = StringField()
    is_caller = BooleanField(default=False)
    is_calltaker = BooleanField(default=False)
    is_primary = BooleanField(default=False)
    direction = StringField(required=True, choices=('in', 'out'), default='in')
    hold = BooleanField(default=False)
    mute = BooleanField(default=False)
    is_send = BooleanField(default=True)
    is_receive = BooleanField(default=True)
    is_active = BooleanField(default=True)
    has_text = BooleanField(default=False)
    has_audio = BooleanField(default=True)
    has_video = BooleanField(default=False)
    send_video = BooleanField(default=True)
    send_audio = BooleanField(default=True)
    send_text = BooleanField(default=True)


class ConferenceEvent(Document):
    room_number = StringField(required=True)
    event = StringField(required=True, choices=('join', 'leave', 'init', 'ringing', 'ringing_queued', \
                                                'queued', 'active', 'closed', 'start_hold', 'end_hold', 'mute', 'end_mute', 'abandoned'))
    event_details = StringField()
    event_time = ComplexDateTimeField(default=datetime.datetime.utcnow)


class ConferenceMessage(Document):
    room_number = StringField(required=True)
    sender_uri = StringField()
    message = StringField()


class Location(Document):
    room_number = StringField(required=True)
    location_id = ObjectIdField(required=True, default=bson.ObjectId)
    time = ComplexDateTimeField(default=datetime.datetime.utcnow)
    updated_at = ComplexDateTimeField(default=datetime.datetime.utcnow)
    ali_format = StringField()
    raw_format = StringField()
    phone_number = StringField()
    category = StringField()
    name = StringField()
    alternate = StringField()
    latitude = FloatField()
    longitude = FloatField()
    radius = FloatField()
    location_point = PointField()
    callback = StringField()
    state = StringField()
    contact = StringField()
    location = StringField()
    service_provider = StringField()
    contact_display = StringField()
    community = StringField()
    secondary = StringField()
    class_of_service = StringField()
    agencies_display = StringField()
    fire_no = StringField()
    ems_no = StringField()
    police_no = StringField()
    otcfield = StringField()
    psap_no = StringField()
    esn = StringField()
    postal = StringField()
    psap_name = StringField()
    pilot_no = StringField()
    descrepancy = BooleanField(default=False)
    '''
    "caller" : {
        "category" : "unknown",
        "agenciesDisplay" : "OTC1122           TEL=QWST",
        "name" : "Mark Twain",
        "callId" : "4e3451d74af1656b09ef633d0e4fac1a@54.243.134.79:5060",
        "alternate" : null,
        "longitude" : "",
        "callback" : "4155551212",
        "state" : "CA",
        "contact" : "<sip:4153054541@54.243.134.79>",
        "radius" : "",
        "location" : "1233 E North Point Street Apt 403",
        "provider" : "",
        "latitude" : "",
        "contactDisplay" : "4155551212",
        "community" : "San Francisco",
        "secondary" : "",
        "pAni" : "4155551212",
        "cls" : "WPH1"
    },
    '''


class AliServer(Document):
    psap_id = ObjectIdField()
    type = StringField(required=True, choices=('wireless', 'wireline'))
    format = StringField()
    ip1  = StringField()
    port1 = IntField(min_value=0)
    ip2 = StringField()
    port2 = IntField(min_value=0)
    name = StringField()


class CallTransferLine(Document):
    line_id = ObjectIdField(required=True, default=bson.ObjectId)
    psap_id = ObjectIdField()
    type = StringField(required=True, choices=('wireless', 'wireline'))
    name = StringField(required=True)
    star_code = StringField(required=True)


class Greeting(Document):
    greeting_id = ObjectIdField(required=True, default=bson.ObjectId)
    psap_id = ObjectIdField()
    user_id = ObjectIdField()
    desc = StringField(required=True)
    group = StringField()


def create_test_data(ip_address="192.168.1.3", asterisk_ip_address="192.168.1.3", asterisk_port=5090):
    #ip_address = "192.168.1.3"
    #asterisk_ip_address = ip_address
    #asterisk_port = "5090"
    psap_obj = Psap()
    psap_obj.name = "SF Psap"
    psap_obj.ip_address = ip_address
    psap_obj.save()

    # create queue
    queue_obj = Queue()
    queue_obj.psap_id = psap_obj.psap_id
    queue_obj.save()

    # create call takers and add to queue
    user_obj = User.add_user("tarun", "tarun")
    queue_memeber_obj = QueueMember()
    queue_memeber_obj.queue_id = queue_obj.queue_id
    queue_memeber_obj.user_id = user_obj.user_id
    queue_memeber_obj.save()

    user_obj = User.add_user("mike", "mike")
    queue_memeber_obj = QueueMember()
    queue_memeber_obj.queue_id = queue_obj.queue_id
    queue_memeber_obj.user_id = user_obj.user_id
    queue_memeber_obj.save()

    user_obj = User.add_user("nate", "nate")
    queue_memeber_obj = QueueMember()
    queue_memeber_obj.queue_id = queue_obj.queue_id
    queue_memeber_obj.user_id = user_obj.user_id
    queue_memeber_obj.save()

    user_obj = User.add_user("matt", "matt")
    queue_memeber_obj = QueueMember()
    queue_memeber_obj.queue_id = queue_obj.queue_id
    queue_memeber_obj.user_id = user_obj.user_id
    queue_memeber_obj.save()

    # create incoming link
    incoming_link_obj = IncomingLink()
    incoming_link_obj.psap_id = psap_obj.psap_id
    incoming_link_obj.name = "default"
    incoming_link_obj.orig_type = "sos_wireless"
    incoming_link_obj.max_channels = 5
    incoming_link_obj.ip_address = asterisk_ip_address
    incoming_link_obj.port = asterisk_port
    incoming_link_obj.called_no = "911"
    incoming_link_obj.queue_id = queue_obj.queue_id
    incoming_link_obj.save()


def remove_room(room_number):
    if room_number is not None:
        print ("deleting room number %r", room_number)
        Call.objects(room_number=room_number).delete()
        ConferenceEvent.objects(room_number=room_number).delete()
        ConferenceParticipant.objects(room_number=room_number).delete()
        Location.objects.get(room_number=room_number).delete()
        Conference.objects.get(room_number=room_number).delete()

def remove_call(room_number=None, status=None):
    if status is not None:
        for confDbObj in Conference.objects(room_number=room_number):
            room_number = confDbObj.room_number
            remove_room(room_number)
        return
    if room_number is not None:
        remove_room(room_number)


'''
Start of OAuth related db models
'''

class Client(Document):
    # human readable name, not required
    name = StringField()
    # human readable description, not required
    description = StringField()

    # creator of the client, not required
    user_id = StringField(required=False, unique=False)

    client_id = StringField(required=True, unique=True)
    client_secret = StringField(required=True, unique=True)

    # public or confidential
    is_confidential = BooleanField(required=True, unique=False, default=True)

    _redirect_uris = ListField(StringField(), required=True, unique=False, default=[])
    _default_scopes = ListField(StringField(), required=True, unique=False, default=[])
    meta = {
        'indexes': [
            'client_id',
            'client_secret'
        ],
    }

    @property
    def client_type(self):
        if self.is_confidential:
            return 'confidential'
        return 'public'

    @property
    def redirect_uris(self):
        return self._redirect_uris

    @property
    def default_redirect_uri(self):
        return self.redirect_uris[0]

    @property
    def default_scopes(self):
        if self._default_scopes:
            return self._default_scopes
        return []

    @property
    def allowed_grant_types(self):
        return ['password', 'authorization_code', 'client_credentials', 'implicit']

    @property
    def user(self):
        return str(self.user_id)

    @classmethod
    def getDefaultRedirectUris(cls):
        return ['https://portal.supportgenie.io', 'https://portal.supportgenie.io', 'https://localhost:9000', 'https://localhost:9000/',
                'https://supportgenie.io/', 'https://supportgenie.io', 'https://www.supportgenie.io', 'https://www.supportgenie.io/',
                'https://localhost:3000', 'https://localhost:3000/']



def create_new_client(name, userid):
    client_id = str(bson.ObjectId())
    client_secret = str(bson.ObjectId())
    try:
        clientObj = Client()
        clientObj.client_secret = client_secret
        clientObj.client_id = client_id
        clientObj.name = name
        clientObj.userid = userid
        clientObj._redirect_uris = Client.getDefaultRedirectUris()
        clientObj._default_scopes = ['user', 'admin']
        clientObj.save()
        print ("created client with id %s and secret %s" % (client_id, client_secret))
    except Exception as e:
        stackTrace = traceback.format_exc()
        print ("exception in create_new_client %r" % e)
        print ("stackTrace is %s" % stackTrace)
        print ("exception in create new client %s" % e.message)


class Grant(Document):
    user_id = StringField(required=False)
    client_id = StringField(required=True)
    code = StringField(required=True)
    redirect_uri = StringField(required=False)
    expires = DateTimeField(required=False)
    _scopes = ListField(StringField())
    meta = {
        'indexes': [
            'code',
            'client_id',
            'user_id'
        ],
    }

    def delete(self):
        log.debug("inside grant delete")
        return Document.delete(self)

    @property
    def scopes(self):
        if self._scopes:
            return self._scopes
        return []


class Token(Document):
    token_id = ObjectIdField(unique=True)
    client_id = StringField(required=True)

    user_id = StringField(required=False)

    # currently only bearer is supported
    token_type = StringField()

    access_token = StringField(required=True, unique=True)
    refresh_token = StringField(required=False, unique=False)
    expires = DateTimeField(required=False)
    _scopes = ListField(StringField())
    meta = {
        'indexes': [
            'id',
            'client_id',
            'user_id'
        ],
    }

    @property
    def scopes(self):
        if self._scopes:
            return self._scopes
        return []

    @property
    def data(self):
        TokenObj = namedtuple('TokenObj', 'id client_id user_id token_type access_token refresh_token scopes expires user')
        tokenData = TokenObj(
            id = str(self.token_id),
            client_id = self.client_id,
            user_id = self.user_id,
            token_type = self.token_type,
            access_token = self.access_token,
            refresh_token = self.refresh_token,
            scopes = self._scopes,
            expires = self.expires,
            user = User.objects.get(calltaker_id=self.user_id))
        return tokenData


'''
End of OAuth related db models
'''



