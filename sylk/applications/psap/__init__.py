
import re
import traceback
import threading
import psutil
import time
from application.notification import IObserver, NotificationCenter, NotificationData
from application.python import Null
from twisted.internet import reactor
from twisted.internet import task
from zope.interface import implements
from lxml import html
import bson

from sipsimple.threading.green import run_in_green_thread
from sylk.applications import SylkApplication, ApplicationLogger
from sipsimple.application import SIPApplication
from sipsimple.streams import MediaStreamRegistry
from sipsimple.streams.msrp.chat import ChatStream
from sipsimple.core import Referral, sip_status_messages
from sipsimple.core import Engine, SIPCoreError, SIPURI, ToHeader, FromHeader, Header, SubjectHeader
from sipsimple.core import ContactHeader, ReferToHeader, RouteHeader
from sipsimple.lookup import DNSLookup
from sipsimple.configuration.settings import SIPSimpleSettings
from sipsimple.configuration.settings import SIPSimpleSettings
from sipsimple.session import IllegalStateError
from sylk.session import Session
from sylk.accounts import get_user_account
from sipsimple.account import Account
from uuid import uuid4

from sylk.accounts import DefaultAccount
from sylk.db.authenticate import authenticate_call, get_calltaker_user
from sylk.db.queue import get_queue_details, get_queue_members
from sylk.db.calltaker import get_available_calltakers, update_calltaker_status, get_user_id
from acd import get_calltakers
import sylk.data.call as call_data
import sylk.data.conference as conf_data
from sylk.data.calltaker import CalltakerData
from sylk.configuration import ServerConfig, SIPConfig
# from sylk.utils import dump_object_member_vars, dump_object_member_funcs, dump_var
from sylk.notifications.call import send_call_update_notification, send_call_active_notification, send_call_failed_notification
from sylk.applications.psap.room import Room
from sylk.location import ali_lookup, dump_ali
from sylk.wamp import publish_update_call_timer, publish_outgoing_call_status, publish_active_call, \
    publish_update_call_ringing, wamp_publish, publish_update_calltaker_status
from sylk.utils import dump_object_member_vars, dump_object_member_funcs

log = ApplicationLogger(__package__)

def get_num_open_files():
    return len(psutil.Process().open_files())

'''
class ReferralError(Exception):
    def __init__(self, error, code=0):
        self.error = error
        self.code = code


class SIPReferralDidFail(Exception):
    def __init__(self, data):
        self.data = data
'''

class RoomNotFoundError(Exception): pass

class RoomData(object):
    __slots__ = ['room', 'incoming_session', 'calltaker_video_streams', 'calltaker_video_session',
                 'calltaker_video_connector', 'caller_video_connector',
                 'call_type', 'has_tty', 'tty_text',
                 'last_tty_0d', 'direction', 'outgoing_calls',
                 'has_audio', 'has_video',
                 'invitation_timer', 'ringing_duration_timer', 'duration_timer',
                 'participants', 'status', 'hold_timer', 'acd_strategy',
                 'ignore_calltakers', 'start_timestamp', 'chat_stream', 'psap_id',
                 'calltaker_server',
                 'incident_id', 'incident_details']
    def __init__(self):
        self.ignore_calltakers = []
        self.participants = []
        self.outgoing_calls = {}
        self.status = 'init'
        self.ringing_duration_timer = None
        self.duration_timer = None
        self.start_timestamp = time.time()
        self.has_tty = False
        self.tty_text = ''
        self.last_tty_0d = False
        self.chat_stream = None
        self.has_audio = False
        self.has_video = False
        self.calltaker_server = ServerConfig.asterisk_server
        self.incident_id = None
        self.incident_details = None
        self.calltaker_video_streams = None
        self.caller_video_connector = None
        self.calltaker_video_connector = None
        self.calltaker_video_session = None

    @property
    def incoming(self):
        return self.direction == 'in'

    @property
    def room_number(self):
        return self.room.room_number

    @property
    def outgoing(self):
        return self.direction == 'out'

    @property
    def is_emergency(self):
        return  self.call_type in ['sos', 'sos_room']

    @property
    def has_text(self):
        return  self.chat_stream is not None

    @property
    def ringing(self):
        return  self.status in ['init', 'ringing', 'ringing_queued']

    @property
    def is_acd_ring_all(self):
        return  self.acd_strategy == 'ring_all'

    @property
    def is_call_active(self):
        return  self.status == 'active'

    @property
    def is_call_on_hold(self):
        return  self.status == 'on_hold'

    @property
    def has_call_ended(self):
        return  self.status in ['closed', 'abandoned', 'timed_out']

    @property
    def calltakers(self):
        calltakers = []
        for participant_data in self.participants.itervalues():
            if participant_data.is_calltaker:
                calltakers.append(participant_data.display_name)
        return calltakers

    @property
    def ringing_calltakers(self):
        calltakers = []
        if self.status == 'ringing':
            for outgoing_call_initializer in self.outgoing_calls.itervalues():
                if outgoing_call_initializer is not None and outgoing_call_initializer.is_calltaker and outgoing_call_initializer.is_ringing:
                    calltakers.append(outgoing_call_initializer.calltaker_name)
        return calltakers

    @property
    def caller(self):
        for participant_data in self.participants.itervalues():
            if participant_data.is_caller:
                return (participant_data.display_name, participant_data.uri, participant_data.is_calltaker)
        raise ValueError("caller missing something is wrong with room %s" % self.room_number)

    @property
    def caller_uri(self):
        for participant_data in self.participants.itervalues():
            if participant_data.is_caller:
                return participant_data.uri
        raise ValueError("caller missing something is wrong with room %s" % self.room_number)

    @property
    def primary_calltaker(self):
        for participant_data in self.participants.itervalues():
            if participant_data.is_calltaker and participant_data.is_primary:
                return participant_data.display_name, participant_data
        return None, None

    def set_primary_calltaker(self, display_name):
        calltaker_data = self.get_calltaker_data(display_name)
        calltaker_data.is_primary = True

    def set_first_calltaker_as_primary(self):
        for participant_data in self.participants.itervalues():
            if participant_data.is_calltaker and not participant_data.on_hold:
                participant_data.is_primary = True
                return

    def get_calltaker_data(self, display_name):
        for participant_data in self.participants.itervalues():
            if participant_data.is_calltaker and (participant_data.display_name == display_name):
                return participant_data
        return None

    def get_calltaker_uri(self, display_name):
        for participant_data in self.participants.itervalues():
            if participant_data.is_calltaker and (participant_data.display_name == display_name):
                return participant_data.uri
        return None

class ParticipantData(object):
    __slots__ = ['display_name', 'uri', 'session', 'direction', 'mute', 'send_audio', 'send_video',
                 'send_text', 'is_caller', 'is_active', 'is_calltaker', 'is_primary', 'on_hold']
    def __init__(self):
        pass

    def __repr__(self):
        return "display_name %r, uri %r, session %r, is_calltaker %r, direction %r, mute %r, send_audio %r, send_video %r, send_text %r, is_caller %r, is_active %r, on_hold %r, is_primary %r" % \
               (self.display_name, self.uri, self.session, self.is_calltaker, self.direction, self.mute, self.send_audio, self.send_video, self.send_text, self.is_caller, self.is_active, self.on_hold, self.is_primary)

#RoomData = namedtuple('RoomData', 'room incoming_session call_type direction outgoing_calls invitation_timer participants')
#ParticipantData = namedtuple('ParticipantData', 'display_name uri session direction mute_audio recv_audio recv_video recv_chat is_caller is_active')

def format_identity(identity):
    if identity.display_name:
        return u'%s <sip:%s@%s>' % (identity.display_name, identity.uri.user, identity.uri.host)
    else:
        return u'sip:%s@%s' % (identity.uri.user, identity.uri.host)


class PSAPApplication(SylkApplication):
    implements(IObserver)

    def __init__(self):
        from sylk.video import VideoConference
        log.info(u'PSAPApplication init')
        call_data.CallData()
        conf_data.ConferenceData()
        self._rooms = {}

        #self.video_conf = VideoConference(SIPApplication.video_mixer)
        #settings = SIPSimpleSettings()
        #self.video_device = VideoDevice(u'Colorbar generator', settings.video.resolution, settings.video.framerate)


    def init_observers(self):
        log.info("PSAPApplication init_observers")
        # this one is used to change the mute, or send status of different media streams
        NotificationCenter().add_observer(self, name='ConferenceParticipantDBUpdated')
        NotificationCenter().add_observer(self, name='CalltakerStatusUpdate')
        NotificationCenter().add_observer(self, name='TTYReceivedChar')
        NotificationCenter().add_observer(self, name='HeldLookup')


    def start(self, main_app):
        log.info(u'PSAPApplication start')
        self.main_app = main_app
        self.video_device = main_app.video_device
        self.init_observers()
        # todo - remove this , only for load testing
        #self.startWampTesting()

    def stop(self):
        log.info(u'PSAPApplication stop')

    # todo - remove this , only for load testing
    def startWampTesting(self):
        log.info("startWampTesting")

        def wamp_testing_cb(self):
            wamp_testing_cb.count = wamp_testing_cb.count + 1
            if (wamp_testing_cb.count % 2000) == 0:
                log.info("sent %d test wamp messages so far", wamp_testing_cb.count)
            log.info("sendTestWampMessages %r", wamp_testing_cb.count)
            self.sendTestWampMessages()
            if wamp_testing_cb.count > 10000000:
                self.wamp_testing_timer.stop()

        wamp_testing_cb.count = 0
        self.wamp_testing_timer = task.LoopingCall(wamp_testing_cb, self)
        self.wamp_testing_timer.start(0.1)  # call every sixty seconds

    # todo - remove this , only for load testing
    def sendTestWampMessages(self):
        log.info("inside sendTestWampMessages")
        message = {'room_number': '7d6afa3cd94d484ebf6ec491caf6a392', 'participants': [
            {'send_video': True, 'direction': u'in', 'is_calltaker': False, 'name': u'+14153054541', 'mute': False,
             'is_active': True, 'has_audio': True, 'is_receive': True, 'is_send': True, 'has_video': False,
             'sip_uri': u'sip:+14153054541@138.68.0.101:5060', 'has_text': False, 'send_text': True,
             'is_primary': False, 'is_caller': True, 'hold': False, 'room_number': u'7d6afa3cd94d484ebf6ec491caf6a392',
             'send_audio': True}], 'command': 'updated',
            'call_data': {'active_participants': [u'+14153054541'], 'is_ani_pseudo': False, 'has_tty': False,
                       'hold_start': u'2018-08-30T19:10:35.224+0000',
                       'caller_uri': u'sip:+14153054541@138.68.0.101:5060',
                       'updated_at': u'2018-08-30T19:10:36.279+0000', 'has_text': False, 'duration': 0,
                       'caller_ani': u'+14153054541', 'answer_time': u'2018-08-30T19:10:35.224+0000',
                       'ali_result': u'none', 'room_number': u'7d6afa3cd94d484ebf6ec491caf6a392', 'has_video': False,
                       'active_calltakers': [], 'callback_time': u'2018-08-30T19:10:35.224+0000', 'location': '',
                       'full_mute': False, 'status': 'ringing', 'direction': u'in',
                       'start_time': u'2018-08-30T19:10:35.224+0000', 'ali_format': u'30WWireless', 'hold': False,
                       'call_type': u'sos', 'has_audio': True, 'secondary_type': u'', 'emergency_type': u'',
                       'caller_name': u'+14153054541', 'callback': False, 'end_time': u'2018-08-30T19:10:35.224+0000',
                       'partial_mute': False}}
        log.info("inside sendTestWampMessages do publish")
        wamp_publish(u'com.emergent.call', message)
        log.info("inside sendTestWampMessages done")

    def get_rooms(self):
        return list(self._rooms.keys())

    def create_room(self, incoming_session, call_type, direction, acd_strategy=None, text_only=False,
                    has_audio=True, has_video=False,
                    psap_id=ServerConfig.psap_id,
                    calltaker_server=ServerConfig.asterisk_server,
                    incident_id=None, incident_details=None):
        room_number = uuid4().hex
        room = Room(psap_id, room_number, text_only)
        room_data = RoomData()
        room_data.room = room
        room_data.call_type = call_type
        room_data.has_audio = has_audio
        room_data.has_video = has_video
        room_data.incoming_session = incoming_session
        room_data.outgoing_calls = {}
        room_data.participants = {}
        room_data.direction = direction
        room_data.invitation_timer = None
        room_data.ringing_duration_timer = None
        room_data.duration_timer = None
        room_data.status = 'init'
        room_data.hold_timer = None
        room_data.acd_strategy = acd_strategy
        room_data.psap_id = psap_id
        room_data.calltaker_server = calltaker_server
        room_data.incident_id = incident_id
        room_data.incident_details = incident_details

        self._rooms[room_number] = room_data

        return (room_number, room_data)

    def get_room(self, room_number):
        if room_number in self._rooms:
            room_data = self._rooms[room_number]
            return room_data.room

        return None

    def get_room_data(self, room_number):
        if room_number in self._rooms:
            return self._rooms[room_number]
        return None

    def get_calltakers_in_room(self, room_number):
        calltakers = []
        if room_number in self._rooms:
            room_data = self._rooms[room_number]
            calltakers = room_data.calltakers
            '''
            for participant_data in room_data.participants.itervalues():
                if participant_data.is_calltaker:
                    calltakers.append(participant_data.display_name)
            '''
        return calltakers

    def get_room_caller(self, room_number):
        if room_number in self._rooms:
            room_data = self._rooms[room_number]
            '''
            for participant_data in room_data.participants.itervalues():
                if participant_data.is_caller:
                    return (participant_data.display_name, participant_data.uri, participant_data.is_calltaker)
            '''
            return room_data.caller
        return (None, None, None)


    '''
    def get_room(self, uri=None, create=False, room_number=None):
        room_uri = self.get_room_uri_str(uri, room_number)

        try:
            room = self._rooms[room_uri]
        except KeyError:
            if create:
                room = Room(room_uri)
                self._rooms[room_uri] = room
                return room
            else:
                raise RoomNotFoundError
        else:
            return room

    '''
    def get_room_uri_str(self, room_number):
        local_ip = SIPConfig.local_ip.normalized
        room_uri = '%s@%s' % (room_number, local_ip)
        return room_uri

    def get_room_uri(self, room_number):
        room_uri_str = self.get_room_uri_str(room_number)
        if not room_uri_str.startswith("sip:"):
            room_uri_str = "sip:%s" % room_uri_str
        return SIPURI.parse(room_uri_str)

    def remove_room(self, room_number):
        self._rooms.pop(room_number, None)

    def get_room_debug_info(self, room_number):
        # get sessions from room
        room = self.get_room(room_number=room_number)
        if room is None:
            return {'room_number': room_number, 'debug_info': 'room not active'}
        return {'room_number' : room_number, 'debug_info' : room.get_debug_info()}

    def get_incident_details(self, call_info):
        incident_id = None
        incident_details = None

        if call_info != None and call_info != "":
            infos = call_info.split(';')
            if len(infos) == 2:
                details = infos[0]
                purpose_field = infos[1]
                purpose_info = purpose_field.split('=')
                if len(purpose_info) == 2 and purpose_info[0] == "purpose" and purpose_info[1] == "nena-IncidentId":
                    details = details.strip('<>')
                    details_parts = details.split(":")
                    if len(details_parts) == 6 and details.startswith("urn:nena:uid:incidentid"):
                        incident_id = details_parts[4]
                        incident_details = details_parts[5]
        return (incident_id, incident_details)

    def incoming_session(self, session, headers):
        log.info(u'New incoming session %s from %s' % (session.call_id, format_identity(session.remote_identity)))
        log.info('New incoming request_uri %r, headers is %r', session.request_uri, headers)
        log.info('headers class is %r', headers.__class__.__name__)
        log.info(u'New incoming request_uri user %s, domain %s' % (session.request_uri.user, session.request_uri.host))

        remote_identity = session.remote_identity
        local_identity = session.local_identity
        peer_address = session.peer_address
        called_number = ""
        calling_number = ""
        authenticated = False
        is_emergency = False
        incoming_link = None
        call_type = ''
        admin_user = ''
        geoloc_ref = None
        incident_id = None
        incident_details = None
        psap_id = ServerConfig.psap_id
        calltaker_server = ServerConfig.asterisk_server
        log.info(u'session.request_uri.user is %s' % (session.request_uri.user))
        if session.request_uri.user == "sos":
            log.info(u'call is sos')
            authenticated = True
            is_emergency = True
            called_number = local_identity.uri.user
            calling_number = remote_identity.uri.user
            call_type = 'sos'

            if 'Call-Info' in headers:
                call_info_header = headers.get('Call-Info', None)
                if call_info_header != None:
                    call_info_data = call_info_header.body
                    if call_info_data != None and call_info_data != "":
                        incident_id, incident_details = self.get_incident_details(call_info_data)

            if 'X-Route' in headers:
                log.info("found X-Route in header")
                route_header = headers.get('X-Route', None)
                if route_header != None:
                    from ...db.psap import get_psap_from_domain, get_psap_from_domain_prefix, get_domain_prefix_from_proxy_domain, get_calltaker_reg_server
                    proxy_domain = route_header.body
                    log.info("proxy_domain is %r", proxy_domain)
                    domain_prefix = get_domain_prefix_from_proxy_domain(proxy_domain)
                    if domain_prefix != None:
                        log.info("domain_prefix is %r", domain_prefix)
                        psap_id = get_psap_from_domain_prefix(domain_prefix)
                        # todo - this is just for temp testing, remove later
                        calltaker_server = get_calltaker_reg_server(domain_prefix)
                        #calltaker_server = "kamailio-reg.supportgenie.io"
                        log.info("psap_id is %r, calltaker_server is %r", psap_id, calltaker_server)
                    else:
                        log.error("error invalid proxy domain %r", proxy_domain)
                        psap_id = get_psap_from_domain(proxy_domain)
                else:
                    log.info("route_header not there or bad")
            else:
                log.info("route_header not there")

            if 'Geolocation' in headers:
                log.info("found Geolocation in header")
                geo_location = headers.get('Geolocation', None)
                if geo_location != None:
                    geoloc_ref = geo_location.body
                    log.info("geoloc_ref is %r", geoloc_ref)
                    if geoloc_ref != None and geoloc_ref != "":
                        if geoloc_ref[0] == '<' and geoloc_ref[-1] == '>':
                            geoloc_ref = geoloc_ref[1:-1]
                        log.info("geoloc_ref is %r", geoloc_ref)

            log.info("authenticated is %r", authenticated)
            direction = 'incoming'
            queue_id = ''
        elif session.request_uri.user == "100":
            authenticated = True
            is_emergency = False
            called_number = local_identity.uri.user
            calling_number = remote_identity.uri.user
            call_type = 'admin'
            direction = 'incoming'
            queue_id = ''
            admin_user = 'mike'
        elif session.request_uri.user == "600":
            authenticated = True
            is_emergency = False
            called_number = local_identity.uri.user
            calling_number = remote_identity.uri.user
            call_type = 'admin'
            direction = 'incoming'
            queue_id = ''

        log.info(u'num open files is %d', get_num_open_files())
        #from mem_top import mem_top
        #log.info(mem_top())
        ''' uncomment for load testing 
        import objgraph
        out = objgraph.most_common_types(limit=20)
        log.info("objgraph most_common_types returned %s", out)
        out = objgraph.growth(limit=20)
        log.info("objgraph growth returned %s", out)
        '''
        #out = objgraph.get_leaking_objects()
        #log.info("objgraph get_leaking_objects returned %r", out)
        # todo remove this
        # this is just temporary to test the mem / resource leak

        send_call_update_notification(self, session, 'init')

        has_audio = False
        has_tty = False
        has_text = False
        has_video = False

        audio_streams = [stream for stream in session.proposed_streams if stream.type=='audio']
        video_streams = [stream for stream in session.proposed_streams if stream.type=='video']
        chat_streams = [stream for stream in session.proposed_streams if stream.type=='chat']
        log.info('audio_streams len %r, streams %r', len(audio_streams), audio_streams)
        log.info('video_streams len %r, streams %r', len(video_streams), video_streams)

        if not audio_streams and not chat_streams:
            log.info(u'Session %s rejected: invalid media, only RTP audio and MSRP chat are supported' % session.call_id)
            session.reject(488)
            send_call_update_notification(self, session, 'reject')
            return
        if audio_streams or video_streams:
            if audio_streams:
                has_audio = True
            if video_streams:
                has_video = True

            session.send_ring_indication()
            send_call_update_notification(self, session, 'ringing')

        if chat_streams:
            has_text = True

        rooms = self.get_rooms()

        log.info("ip %r, port %r, called_number %r, called_uri %r, from_uri %r, rooms %r",
            peer_address.ip, peer_address.port, local_identity.uri.user, local_identity.uri, remote_identity.uri, rooms)
        # first verify the session
        if not authenticated:
            log.info("call not authenticated")
            (authenticated, call_type, incoming_link, calltaker_obj, called_number, calling_number) = authenticate_call(peer_address.ip, peer_address.port, local_identity.uri.user, remote_identity.uri, rooms)
        log.info("called_number %s, calling_number %s", called_number, calling_number)
        if not authenticated:
            log.info("call not authenticated, reject it")
            session.reject(403)
            send_call_update_notification(self, session, 'reject')
            return

        NotificationCenter().add_observer(self, sender=session)

        if (call_type == 'sos') or (call_type == 'outgoing') or (call_type == 'outgoing_calltaker') or (call_type == 'admin'):
            queue_details = None
            acd_strategy = None
            ignore_calltakers = None

            if call_type == 'sos':
                session.is_calltaker = False
                server = calltaker_server
                if (incoming_link != None) and hasattr(incoming_link, "queue_id") and (incoming_link.queue_id != None):
                    queue_details = get_queue_details(incoming_link.queue_id)
                    queue_members = get_queue_members(incoming_link.queue_id)
                    user_ids = [str(queue_member.user_id) for queue_member in queue_members]
                    acd_strategy = queue_details.acd_strategy
                    calltakers = get_calltakers(acd_strategy, user_ids)
                    sip_uris = ["sip:%s@%s" % (calltaker.username, server) for calltaker in calltakers.itervalues()]
                    [self.set_calltaker_busy(user_id=user_id) for user_id in user_ids]
                    ignore_calltakers = [calltaker.username for calltaker in calltakers.itervalues()]
                else:
                    acd_strategy = 'ring_all'
                    calltakers, user_ids = get_available_calltakers(psap_id)
                    sip_uris = ["sip:%s@%s" % (calltaker, server) for calltaker in calltakers]
                    [self.set_calltaker_busy(user_id=user_id) for user_id in user_ids]
                    ignore_calltakers = [calltaker for calltaker in calltakers]

                log.info("sip_uris is %r", sip_uris)
                forward_to_calltaker=True

                # check overflow handling
                if len(sip_uris) == 0:
                    log.info("check for overflow handling")
                    if self.handle_overflow_call(psap_id, session):
                        return

                # add these calltakers to ignore list so we do not bother them again
            elif call_type == 'admin':
                if admin_user != '':
                    server = calltaker_server
                    sip_uris = ["sip:%s@%s" % (admin_user, server)]
                    user_id = get_user_id(admin_user)
                    log.info("sip_uris is %r", sip_uris)
                    self.set_calltaker_busy(user_id=user_id)
                    forward_to_calltaker = True
                    # add these calltakers to ignore list so we do not bother them again
                    ignore_calltakers = [admin_user]
                else:
                    sip_uris = []
                    forward_to_calltaker = True
                    ignore_calltakers = []
            else:
                if call_type == 'outgoing':
                    session.is_calltaker = True
                    session.calltaker_name = remote_identity.uri.user
                    outgoing_gateway = ServerConfig.outgoing_gateway
                    e164_number = self._format_number_to_e164(called_number)
                    sip_uri = 'sip:{}@{}'.format(e164_number, outgoing_gateway)
                    sip_uris = [sip_uri]
                    # clear abandoned calls for this user
                    #clear_abandoned_calls(local_identity.uri.user)
                    forward_to_calltaker=False
                elif call_type == 'outgoing_calltaker':
                    session.is_calltaker = True
                    session.calltaker_name = remote_identity.uri.user
                    forward_to_calltaker=True
                    server = calltaker_server
                    sip_uri = 'sip:{}@{}'.format(called_number, server)
                    sip_uris = [sip_uri]

            if (call_type == 'outgoing') or (call_type == 'outgoing_calltaker'):
                direction = 'out'
                is_call_from_calltaker = True
            else:
                direction = 'in'
                is_call_from_calltaker = False

            (room_number, room_data) = self.create_room(session, call_type, direction=direction,
                                                        acd_strategy=acd_strategy, text_only=has_text,
                                                        has_audio=has_audio, has_video=has_video,
                                                        psap_id=psap_id, calltaker_server=calltaker_server,
                                                        incident_id=incident_id, incident_details=incident_details)
            session.room_number = room_number
            if ignore_calltakers is not None:
                room_data.ignore_calltakers = ignore_calltakers

            ali_format = ''
            caller_ani = calling_number
            #caller_ani = remote_identity.uri.user
            caller_name = remote_identity.uri.user
            #called_number = local_identity.uri.user
            caller_uri = str(remote_identity.uri)
            called_uri = str(local_identity.uri)
            if (call_type == 'sos') and (incoming_link != None) and hasattr(incoming_link, 'ali_format') and (incoming_link.ali_format != ''):
                log.info('inoming_link.ali_format is %r', incoming_link.ali_format)
                # just a temporary change for warren county
                #lookup_number = local_identity.uri.user
                #lookup_number = called_number
                #if lookup_number[-1:] == '#':
                #    lookup_number = lookup_number[:-1]
                #if lookup_number.startswith("*40"):
                #    lookup_number = lookup_number[3:]
                #caller_ani = lookup_number
                caller_name = calling_number
                #called_number = remote_identity.uri.user
                #caller_uri = str(remote_identity.uri)
                #lookup_number = remote_identity.uri.user
                # make sure there is no + prefix in the number and it is 10 digits long
                # this should be done in incoming link
                #if lookup_number.startswith('+1'):
                #    lookup_number = lookup_number[2:]
                #elif lookup_number.startswith('1'):
                #    lookup_number = lookup_number[1:]
                log.info('calling ali_lookup for room %r, user %r, format %r', room_number, caller_ani, incoming_link.ali_format)
                ali_format = incoming_link.ali_format

            if (len(sip_uris) == 0) and (call_type == 'sos'):
                room_data.status = 'ringing_queued'
            else:
                room_data.status = 'ringing'
            link_id = None
            if incoming_link != None:
                link_id = incoming_link.link_id
            NotificationCenter().post_notification('ConferenceCreated', self,
                                                   NotificationData(room_number=room_number, direction=direction,
                                                                    call_type=call_type, status=room_data.status,
                                                                    psap_id=psap_id,
                                                                    primary_queue_id=incoming_link.queue_id if hasattr(incoming_link, 'queue_id') else None,
                                                                    link_id=link_id,
                                                                    caller_ani=caller_ani,
                                                                    caller_uri=caller_uri,
                                                                    called_uri=called_uri,
                                                                    caller_name=caller_name,
                                                                    called_number=called_number,
                                                                    ali_format=ali_format,
                                                                    has_audio=has_audio, has_text=has_text, has_video=has_video, has_tty=has_tty,
                                                                    incident_id=incident_id, incident_details=incident_details))

            if (call_type == 'sos'):
                if geoloc_ref != None:
                    # do this in the background
                    # and also after conf room is created
                    NotificationCenter().post_notification('HeldLookup', self,
                                                           NotificationData(room_number=room_number,
                                                                            psap_id=psap_id,
                                                                            geoloc_ref=geoloc_ref,
                                                                            caller_name=caller_name))
                elif hasattr(incoming_link, 'ali_format') and (incoming_link.ali_format != ''):
                    ali_lookup(room_number, psap_id, caller_ani, incoming_link.ali_format)
                else:
                    lookup_number = caller_ani
                    if len(lookup_number) > 0 and lookup_number[0] == '+':
                        lookup_number = lookup_number[1:]
                    if len(lookup_number) > 0 and lookup_number[0] == '1':
                        lookup_number = lookup_number[1:]
                    log.info("do lookup for room_number %r, lookup_number %r", room_number, lookup_number)
                    ali_lookup(room_number, psap_id, lookup_number, "30WWireless")

            self.add_incoming_participant(display_name=calling_number, sip_uri=str(remote_identity.uri), session=session, is_caller=True, is_calltaker=is_call_from_calltaker)
            if direction == 'out':
                publish_outgoing_call_status(room_number, remote_identity.uri.user, 'ringing')

            if queue_details and queue_details.ring_time is not None:
                # start call timer
                ring_time = queue_details.ring_time
            else:
                ring_time = 60
            log.info("ringing timeout for conf room %r is %r", room_number, ring_time)

            try:
                ringing_timer = reactor.callLater(ring_time, self.on_ringing_timeout, session, room_number)

                def ringing_duration_timer_cb(room_number):
                    ringing_duration_timer_cb.duration = ringing_duration_timer_cb.duration + 1
                    publish_update_call_timer(psap_id, room_number, 'ringing', ringing_duration_timer_cb.duration)

                ringing_duration_timer_cb.duration = 0
                ringing_duration_timer = task.LoopingCall(ringing_duration_timer_cb, room_number)
                ringing_duration_timer.start(1)  # call every sixty seconds
                room_data.invitation_timer = ringing_timer
                room_data.ringing_duration_timer = ringing_duration_timer
                log.info("ringing_timer set ")
            except Exception as e:
                log.error("exception in setting ringing_timer %r", e)

            # create the conference room here
            #get_conference_application().incoming_session(self.incoming_session, room_number=room_number)
            if direction == 'out':
                caller_identity = "sip:%s@%s" % (ServerConfig.from_number, SIPConfig.local_ip)
            else:
                caller_identity = calling_number
                #if call_type == 'sos':
                #    caller_identity = lookup_number
                #else:
                #    caller_identity = str(session.remote_identity.uri)
            log.info("outgoing caller is %s", caller_identity)
            for sip_uri in sip_uris:
                log.info("create outgoing call to sip_uri %r", sip_uri)
                # create an outbound session here for calls to calltakers
                log.info('creating outgoing_call_initializer is_calltaker %r', forward_to_calltaker)
                outgoing_call_initializer = OutgoingCallInitializer(target_uri=sip_uri, room_uri=self.get_room_uri(room_number),
                                                                    has_video=has_video, has_chat=has_text,
                                                                    caller_identity=caller_identity, is_calltaker=forward_to_calltaker, add_failed_event=False)
                ''' old code '''
                '''
                outgoing_call_initializer = OutgoingCallInitializer(target=sip_uri,
                                                                   audio=True,
                                                                   room_number=room_number,
                                                                   user=remote_identity.uri.user,
                                                                    app=self,
                                                                    is_calltaker=not is_calltaker)
                '''
                outgoing_call_initializer.start()
                room_data.outgoing_calls[str(sip_uri)] = outgoing_call_initializer
                #self.invited_parties[sip_uri] = outgoing_call_initializer
        elif call_type == 'sos_room':
            room_number = local_identity.uri.user
            room_data = self.get_room_data(room_number)
            session.is_calltaker = True
            session.calltaker_name = remote_identity.uri.user
            session.room_number = room_number
            log.info("join call to room %r", room_number)
            mute_audio = False
            if 'X-Emergent-mute' in headers:
                mute_header = headers.get('X-Emergent-mute', None)
                if mute_header.body == '1':
                    log.info("need to mute this call")
                    mute_audio = True

            self.add_incoming_participant(display_name=remote_identity.uri.user, sip_uri=str(remote_identity.uri), session=session, is_caller=False, is_calltaker=True, mute_audio=mute_audio)
            # todo add handling for ringing calls here
            '''
            todo - check if this needs to be moved to session did start
            self.add_session_to_room(session)
            room_data = self.get_room_data(room_number)
            if room_data.status != 'active':
                calltakers = self.get_calltakers_in_room(room_number)
                log.info('outgoing_session_did_start send active notification to calltakers %s', calltakers)
                room_data.status = 'active'
                NotificationCenter().post_notification('ConferenceActive', self,
                                                       NotificationData(room_number=room_number, calltakers=calltakers))
                (display_name, uri, is_calltaker) = self.get_room_caller(room_number)
                if (display_name is not None) and is_calltaker:
                    publish_outgoing_call_status(room_number, display_name, 'active')
            '''
            incoming_sdp_val = None
            if hasattr(room_data.incoming_session, 'is_sdp_passthrough') and room_data.incoming_session.is_sdp_passthrough:
                log.info("sos_room accept set sdp_val to %r", room_data.incoming_session.remote_sdp)
                incoming_sdp_val = room_data.incoming_session.remote_sdp
            reactor.callLater(0, self.accept_session, session, room_number, incoming_sdp_val)
            if room_data.ringing:
                # also cancel the ringing timer and end ringing call
                if room_data.ringing_duration_timer is not None:
                    room_data.ringing_duration_timer.stop()
                    room_data.ringing_duration_timer = None
                if room_data.invitation_timer is not None:
                    room_data.invitation_timer.cancel()
                    room_data.invitation_timer = None
                ''' This moved to add_session_to_room
                if session.is_calltaker:
                    session.is_primary = True
                '''
                log.info('room_data.outgoing_calls %r', room_data.outgoing_calls)
                for target, outgoing_call_initializer in room_data.outgoing_calls.iteritems():
                    log.info('target %r', target)
                    log.info('outgoing_call_initializer %r', outgoing_call_initializer)
                    outgoing_call_initializer.cancel_call()
                sdp_val = None
                if hasattr(session,'is_sdp_passthrough') and session.is_sdp_passthrough:
                    log.info("sos_room accept set session sdp_val to %r", session.remote_sdp)
                    sdp_val = session.remote_sdp
                reactor.callLater(0, self.accept_session, room_data.incoming_session, room_number, sdp_val)
            self.set_calltaker_busy(username=str(remote_identity.uri.user))
            NotificationCenter().post_notification('ConferenceAnswered', self,
                                                   NotificationData(room_number=room_number,
                                                                    display_name=str(remote_identity.uri.user),
                                                                    is_calltaker=True, status=room_data.status,
                                                                    psap_id=room_data.psap_id))

    def invite_to_conference(self, room_number, call_from, phone_number):
        log.info("invite_to_conference for room %s, phone %s", room_number, phone_number)
        if phone_number.startswith('R'):
            self.hook_flash_transfer(room_number, phone_number)
            return

        room_data = self.get_room_data(room_number)
        is_calltaker = False
        calltaker_user = get_calltaker_user(phone_number)
        if calltaker_user != None:
            is_calltaker = True
            server = room_data.calltaker_server
            sip_uri = "sip:%s@%s" % (phone_number, server)
            self.set_calltaker_busy(user_id=str(calltaker_user.user_id))
        else:
            e164_number = self._format_number_to_e164(phone_number)
            outgoing_gateway = ServerConfig.outgoing_gateway
            sip_uri = 'sip:{}@{}'.format(e164_number, outgoing_gateway)
        log.info("sip_uri is %s", sip_uri)

        publish_outgoing_call_status(room_number, call_from, 'ringing')
        outgoing_call_initializer = OutgoingCallInitializer(target_uri=sip_uri, room_uri=self.get_room_uri(room_number),
                                                            caller_identity=room_data.incoming_session.remote_identity,
                                                            is_calltaker=is_calltaker, inviting_calltaker=call_from)
        outgoing_call_initializer.start()
        room_data.outgoing_calls[str(sip_uri)] = outgoing_call_initializer
        return outgoing_call_initializer.ref_id

    def cancel_invite_to_conference(self, room_number, call_from, ref_id):
        room_data = self.get_room_data(room_number)
        for outgoing_call_initializer in room_data.outgoing_calls.itervalues():
            if outgoing_call_initializer.ref_id == ref_id:
                outgoing_call_initializer.cancel_call()
                publish_outgoing_call_status(room_number, call_from, 'cancel')

    def handle_overflow_call(self, psap_id, session):
        from ...db.psap import get_overflow_uri
        overflow_uri, psap_name = get_overflow_uri(psap_id)
        if overflow_uri != None:
            target_uri = SIPURI.parse(overflow_uri)
            extra_headers = []
            extra_headers.append(Header('X-Emergent-Reason', str("Overflow call from %s" % psap_name)))
            session.transfer(target_uri, extra_headers=extra_headers)
            return True
        return False

    def _format_number_to_e164(self, phone_number):
        if len(phone_number) == 10:
            return "+1%s" % phone_number
        if phone_number[0] != '+':
            return "+%s" % phone_number
        return phone_number

    def _get_non_calltaker_sessions(self, room_number):
        sessions = []
        room_data = self.get_room_data(room_number)
        if room_data is not None:
            for participant in room_data.participants.itervalues():
                if not participant.is_calltaker:
                    sessions.append(participant.session)
        return sessions


    def send_dtmf(self, room_number, dtmf_digit):
        sessions = self._get_non_calltaker_sessions(room_number)
        for session in sessions:
            session.send_dtmf(dtmf_digit)

    def hook_flash_transfer(self, room_number, phone_number):
        log.info('hook_flash_transfer for %s, %s', room_number, phone_number)
        room_data = self.get_room_data(room_number)
        psap_id = room_data.psap_id
        if room_data is not None:
            session = room_data.incoming_session
            NotificationCenter().post_notification('ConferenceHookFlashTrasnfer', self,
                                                   NotificationData(room_number=room_number,
                                                                    phone_number=phone_number[1:],
                                                                    psap_id=psap_id))
            session.send_dtmf('R')
            digits_to_send = phone_number[1:]
            def send_digits():
                log.info('hook_flash_transfer send digits %s, %s', room_number, digits_to_send)
                for dtmf_digit in digits_to_send:
                    session.send_dtmf(dtmf_digit)
            reactor.callLater(3, send_digits)

    def star_code_transfer(self, room_number, star_code):
        log.info('star_code_transfer for %s, %s', room_number, star_code)
        room_data = self.get_room_data(room_number)
        psap_id = room_data.psap_id
        if room_data is not None:
            session = room_data.incoming_session
            NotificationCenter().post_notification('ConferenceHookFlashTrasnfer', self,
                                                   NotificationData(room_number=room_number,
                                                                    phone_number=star_code, \
                                                                    psap_id=psap_id))
            session.send_dtmf('R')
            def send_digits():
                for dtmf_digit in star_code:
                    log.info('star_code_transfer send digit %s', dtmf_digit)
                    session.send_dtmf(dtmf_digit)
            reactor.callLater(3, send_digits)


    def on_ringing_timeout(self, incoming_session, room_number):
        log.info("on_ringing_timeout")
        log.info("timed out ringing for conf room %r", room_number)

        room = self.get_room(room_number)
        room_data = self.get_room_data(room_number)
        room_data.invitation_timer = None
        if room and (not room.started) and room_data.ringing:
            self.end_ringing_call(room_number)
            if room_data and (room_data.outgoing):
                status = 'timed_out'
            else:
                status = 'abandoned'
            room_data.status = status
            psap_id = room_data.psap_id
            send_call_update_notification(self, incoming_session, status)
            NotificationCenter().post_notification('ConferenceUpdated', self,
                                                   NotificationData(room_number=room_number, status=status,
                                                                    psap_id=psap_id))
            NotificationCenter().post_notification('ConferenceTimedOut', self,
                                                   NotificationData(room_number=room_number,
                                                                    status=status,
                                                                    psap_id=psap_id))
        else:
            log.error("Error on_ringing_timeout recvd for active call %r", room_number)

    def end_ringing_call(self, room_number):
        room = self.get_room(room_number)
        room_data = self.get_room_data(room_number)
        if room_data.ringing_duration_timer != None:
            room_data.ringing_duration_timer.stop()
            room_data.ringing_duration_timer = None
        if room_data.invitation_timer != None:
            room_data.invitation_timer.cancel()
            room_data.invitation_timer = None
        if not room.started:
            room_data = self.get_room_data(room_number)
            for outgoing_call_initializer in room_data.outgoing_calls.itervalues():
                outgoing_call_initializer.cancel_call()
            log.info("end_ringing_call check room_data.participants")
            for participant in room_data.participants.itervalues():
                if participant.is_calltaker:
                    self.set_calltaker_available(username=participant.display_name)
            log.info('room_data.incoming_session %r end', room_data.incoming_session)
            if room_data.incoming_session.state == 'incoming':
                room_data.incoming_session.reject(code=408, reason="no user picked up")
            elif room_data.incoming_session.state == 'connected':
                room_data.incoming_session.end()
            self.remove_room(room_number)
            # todo add more acd handling here
            # todo mark the conference as ended

    def incoming_subscription(self, request, data):
        request.reject(405)

    def incoming_referral(self, refer_request, data):
        from_header = data.headers.get('From', Null)
        to_header = data.headers.get('To', Null)
        refer_to_header = data.headers.get('Refer-To', Null)
        if Null in (from_header, to_header, refer_to_header):
            refer_request.reject(400)
            return

        log.info(u'Room %s - join request from %s to %s' % ('%s@%s' % (to_header.uri.user, to_header.uri.host), from_header.uri, refer_to_header.uri))

        # todo - add validation here
        #try:
        #    self.validate_acl(data.request_uri, from_header.uri)
        #except ACLValidationError:
        #    log.info(u'Room %s - invite participant request rejected: unauthorized by access list' % data.request_uri)
        #    refer_request.reject(403)
        #    return
        referral_handler = IncomingReferralHandler(refer_request, data)
        referral_handler.start()

    def incoming_message(self, request, data):
        request.reject(405)

    def outgoing_session_lookup_failed(self, room_number, sip_uri):
        log.info("set outgoing_session_lookup_failed %s , %s", room_number, str(sip_uri))
        room_data = self.get_room_data(room_number)
        if room_data is not None:
            if sip_uri in room_data.outgoing_calls:
                # todo send event that the call failed
                outgoing_call_initializer = room_data.outgoing_calls[str(sip_uri)]
                del room_data.outgoing_calls[str(sip_uri)]
                if outgoing_call_initializer.is_calltaker:
                    # get the calltaker name from
                    target_uri = SIPURI.parse(str(sip_uri))
                    log.info("set user %s available", target_uri.user)
                    self.set_calltaker_available(username=target_uri.user)

            if len(room_data.outgoing_calls) == 0:
                # todo add handling here, put the call in queue?
                pass

    def outgoing_session_did_fail(self, session, sip_uri, failure_code, reason, add_failed_event=True):
        log.info('outgoing_session_did_fail session %r, sip_uri %r, failure_code %r, reason %r', session, sip_uri, failure_code, reason)
        room_number = session.room_number
        log.info('outgoing_session_did_fail room_number %r', room_number)
        room_data = self.get_room_data(room_number)
        psap_id = room_data.psap_id
        #room = self.get_room(room_number)
        if add_failed_event:
            # get the target name
            sip_uri_obj = SIPURI.parse(str(sip_uri))
            NotificationCenter().post_notification('ConferenceParticipantFailed', self,
                                                   NotificationData(room_number=room_number,
                                                                    display_name=sip_uri_obj.user,
                                                                    psap_id=psap_id))
        if room_data is not None:
            if str(sip_uri) in room_data.outgoing_calls:
                log.info('found room_data.outgoing_calls ')
                # todo send event that the call failed
                outgoing_call_initializer = room_data.outgoing_calls[str(sip_uri)]
                del room_data.outgoing_calls[str(sip_uri)]
                if room_data.direction == 'out':
                    (display_name, uri, is_calltaker) = self.get_room_caller(room_number)
                    if (display_name is not None) and is_calltaker:
                        publish_outgoing_call_status(room_number, display_name, 'failed')
                if outgoing_call_initializer.is_calltaker:
                    # get the calltaker name from
                    target_uri = SIPURI.parse(str(sip_uri))
                    log.info("set user %s available", target_uri.user)
                    self.set_calltaker_available(username=target_uri.user)
            else:
                log.info('not found room_data.outgoing_calls for %r', str(sip_uri))


            # todo this is wrong and a bug, fix this
            if (len(room_data.outgoing_calls) == 0):
                if room_data.is_emergency and not room_data.is_call_active:
                      # todo add handling here, put the call in queue?
                    log.info("put call in ringing queue")
                    room_data.status = 'ringing_queued'
                    NotificationCenter().post_notification('ConferenceUpdated', self,
                                                           NotificationData(room_number=room_number,
                                                                            status='ringing_queued'))
                else:
                    log.info("send bad number dialed")
                    if not room_data.is_call_active:
                        room_data.incoming_session.reject(code=404, reason="bad number dialed")
                        NotificationCenter().post_notification('ConferenceUpdated', self,
                                                               NotificationData(room_number=room_number,
                                                                                status='failed'))
                    '''
                    else:
                        display_name = str(session.remote_identity.uri.user)
                        NotificationCenter().post_notification('ConferenceCallFailed', self,
                                                               NotificationData(room_number=room_number,
                                                                                display_name=display_name,
                                                                                is_calltaker=session.is_calltaker,
                                                                                reason=reason))
                    '''

    def outgoing_session_is_ringing(self, room_number, target):
        room = self.get_room(room_number)
        room_data = self.get_room_data(room_number)
        psap_id = room_data.psap_id
        if not room_data.is_call_active:
            # update ringing calltakers
            publish_update_call_ringing(psap_id, room_number, room_data.ringing_calltakers)

        if room and room.started:
            # get the target name
            target_uri = SIPURI.parse(str(target))
            NotificationCenter().post_notification('ConferenceParticipantRinging', self,
                                                   NotificationData(room_number=room_number, display_name=target_uri.user,
                                                                    psap_id=psap_id))

    def outgoing_session_will_start(self, sip_uri, session):
        room_number = session.room_number
        log.info('outgoing_session_will_start for sip_uri %s, session %r, room_number %s', sip_uri, session, room_number)
        '''
        moving this to session did start
        room = self.get_room(room_number)
        room_data = self.get_room_data(room_number)
        if not room.started:
            # streams = [stream for stream in (audio_stream, chat_stream, transfer_stream) if stream]
            # reactor.callLater(4 if audio_stream is not None else 0, self.accept_session, session, streams)
            reactor.callLater(0, self.accept_session, room_data.incoming_session)

            if room_data.ringing_duration_timer is not None:
                room_data.ringing_duration_timer.stop()
                room_data.ringing_duration_timer = None
            if room_data.invitation_timer is not None:
                room_data.invitation_timer.cancel()
                room_data.invitation_timer = None
            #This moved to add_session_to_room
            #if session.is_calltaker:
            #    session.is_primary = True
            #
            log.info('room_data.outgoing_calls %r', room_data.outgoing_calls)
            for target, outgoing_call_initializer in room_data.outgoing_calls.iteritems():
                log.info('target %r', target)
                log.info('outgoing_call_initializer %r', outgoing_call_initializer)

                if target != str(sip_uri):
                    outgoing_call_initializer.cancel_call()
            # room_data.outgoing_calls = {}
        '''

    def outgoing_session_did_start(self, sip_uri, is_calltaker, session):
        room_number = session.room_number
        log.info('outgoing_session_did_start for sip_uri %s, session %r, room_number %s', sip_uri, session, room_number)

        room = self.get_room(room_number)
        room_data = self.get_room_data(room_number)
        sdp_val = None
        if session != None and hasattr(session, 'is_sdp_passthrough') and session.is_sdp_passthrough:
            log.info("outgoing_session_did_start set sdp_val to %r", session.remote_sdp)
            sdp_val = session.remote_sdp
            room_data.calltaker_video_session = session

        log.info('outgoing_session_did_start session streams %r, proposed_streams %r', session.streams, session.proposed_streams)
        if not room.started:
            # streams = [stream for stream in (audio_stream, chat_stream, transfer_stream) if stream]
            # reactor.callLater(4 if audio_stream is not None else 0, self.accept_session, session, streams)
            reactor.callLater(0, self.accept_session, room_data.incoming_session, room_number, sdp_val = sdp_val)

            incoming_session = room_data.incoming_session
            incoming_video_streams = [stream for stream in incoming_session.proposed_streams if stream.type == 'video']
            incoming_video_stream = incoming_video_streams[0] if incoming_video_streams else None

            if session.streams != None:
                outgoing_video_streams = [stream for stream in session.streams if stream.type == 'video']
                #outgoing_video_stream = outgoing_video_streams[0] if outgoing_video_streams else None
                room_data.calltaker_video_streams = outgoing_video_streams
                '''
                log.info("check for video producers and consumers outgoing_video_stream %r, incoming_video_stream %r",
                         outgoing_video_stream, incoming_video_stream)
                log.info("check for video producers and consumers transport %r, incoming_video_stream %r",
                            outgoing_video_stream._transport, incoming_video_stream._transport)
                # todo - use a tee to send the incoming video to all participants in future, for now it only goes to one
                if outgoing_video_stream != None and outgoing_video_stream._transport != None \
                    and incoming_video_stream != None and incoming_video_stream._transport != None:
                    log.info("look at adding video producers to consumers")
                    calltaker_video_producer = outgoing_video_stream._transport.remote_video
                    calltaker_video_consumer = outgoing_video_stream._transport.local_video

                    caller_video_producer = incoming_video_stream._transport.remote_video
                    caller_video_consumer = incoming_video_stream._transport.local_video
                    if calltaker_video_producer != None and caller_video_consumer != None:
                        log.info("Add producer to caller video")
                        caller_video_consumer.producer = calltaker_video_producer
                    if calltaker_video_consumer != None and caller_video_producer != None:
                        calltaker_video_consumer.producer = caller_video_producer
                        log.info("Add producer to calltaker video")
                '''
            else:
                log.error("session.streams is None")


            if room_data.ringing_duration_timer is not None:
                room_data.ringing_duration_timer.stop()
                room_data.ringing_duration_timer = None
            if room_data.invitation_timer is not None:
                room_data.invitation_timer.cancel()
                room_data.invitation_timer = None
            ''' This moved to add_session_to_room
            if session.is_calltaker:
                session.is_primary = True
            '''
            log.info('room_data.outgoing_calls %r', room_data.outgoing_calls)
            for target, outgoing_call_initializer in room_data.outgoing_calls.iteritems():
                log.info('target %r', target)
                log.info('outgoing_call_initializer %r', outgoing_call_initializer)

                if target != str(sip_uri):
                    outgoing_call_initializer.cancel_call()
        NotificationCenter().post_notification('ConferenceAnswered', self,
                                               NotificationData(room_number=room_number, display_name=str(sip_uri.user),
                                                                is_calltaker=is_calltaker, status=room_data.status,
                                                                psap_id=room_data.psap_id))

        #todo - add proper value of is_calltaker
        #self.add_outgoing_participant(display_name=sip_uri.user, sip_uri=str(sip_uri), session=session, is_calltaker=True, is_primary=session.is_primary)
        self.add_outgoing_participant(display_name=sip_uri.user, sip_uri=str(sip_uri), session=session, is_calltaker=is_calltaker)
        sdp_passthrough = False
        if session != None and hasattr(session, 'is_sdp_passthrough') and session.is_sdp_passthrough:
            sdp_passthrough = True
        self.add_session_to_room(room_number, session, sdp_passthrough)
        del room_data.outgoing_calls[str(sip_uri)]
        if is_calltaker and room_data.is_emergency:
            dump_ali(room_number, calltaker=str(sip_uri.user))

        '''
        room_data = self.get_room_data(room_number)
        if room_data.status != 'active':
            calltakers = self.get_calltakers_in_room(room_number)
            log.info('outgoing_session_did_start send active notification to calltakers %s', calltakers)
            room_data.status = 'active'
            NotificationCenter().post_notification('ConferenceActive', self,
                                                   NotificationData(room_number=room_number, calltakers=calltakers))
            (display_name, uri, is_calltaker) = self.get_room_caller(room_number)
            if (display_name is not None) and is_calltaker:
                publish_outgoing_call_status(room_number, display_name, 'active')
        else:
            publish_active_call(sip_uri.user, room_number)
            # if the outgoing call was for a calltaker send active status notification
        '''

            #else:
        #    session.end()

    '''
    def add_outgoing_session(self, session):
        log.info(u'add_outgoing_session for session %r', session)
        NotificationCenter().add_observer(self, sender=session)
        room_number = session.room_number
        log.info(u'add_outgoing_session for room_number %s' % room_number)
        room = self.get_room(room_number)
        room.start()
        room.add_session(session)
        #room_uri = self.get_room_uri(uri=None, room_number=room_number)
        #self.add_participant(session, room_uri)
        self.add_participant(session)
    '''

    def accept_session(self, session, room_number, sdp_val=None):
        log.info("accept session for room %r", room_number)
        room_data = self.get_room_data(room_number)
        if session.state == 'incoming':
            audio_streams = [stream for stream in session.proposed_streams if stream.type == 'audio']
            video_streams = [stream for stream in session.proposed_streams if stream.type == 'video']
            chat_streams = [stream for stream in session.proposed_streams if stream.type == 'chat']
            log.info("num audio_streams %r ", len(audio_streams))
            log.info("num video_streams %r ", len(video_streams))
            log.info("num chat_streams %r ", len(chat_streams))
            audio_stream = audio_streams[0] if audio_streams else None
            video_stream = video_streams[0] if video_streams else None
            chat_stream = chat_streams[0] if chat_streams else None
            streams = [stream for stream in (audio_stream, chat_stream, video_stream) if stream]
            room_data.chat_stream = chat_stream
            if chat_stream is not None:
                chat_stream.room_number = room_number
                notification_center = NotificationCenter()
                notification_center.add_observer(self, sender=chat_stream)
                room_data.chat_stream = chat_stream
            '''
            for stream in session.proposed_streams:
                if stream in streams:
                    if isinstance(stream, ChatStream):
                        log.info("adding chatstream for room %s", room_number)
                        notification_center = NotificationCenter()
                        stream.room_number = room_number
                        notification_center.add_observer(self, sender=stream)
                        room_data.chat_stream = stream
            '''

            try:
                log.info("accept incoming session %r", session)
                session.accept(streams, is_focus=True, sdp_val=sdp_val)
            except IllegalStateError:
                pass


    def remove_session_from_room(self, room_number, session):
        log.info('remove_session_from_room for session %r, room_number %r', session, room_number)
        try:
            room = self.get_room(room_number)
            if room is None:
                # todo check more here
                log.info('room is none for %r', room_number)
                return
        except RoomNotFoundError:
            log.info('in _NH_SIPSessionDidEnd RoomNotFoundError')
            return
        room_data = self.get_room_data(room_number)
        psap_id = room_data.psap_id

        if not room.started and (room_data.status in ['ringing', 'ringing_queued']):
            log.info('remove_session room not started yet')
            if session == room_data.incoming_session:
                log.info('remove_session room not started yet, end_ringing_call')
                self.end_ringing_call(room_number)
                # add event that the user cancelled

            self.remove_room(room_number)
            room.stop()
            if room_data.outgoing:
                room_data.status = 'cancel'
            else:
                room_data.status = 'abandoned'

            NotificationCenter().post_notification('ConferenceUpdated', self,
                                                   NotificationData(room_number=room_number,
                                                                    status=room_data.status))
            return
        '''
        room_uri = self.get_room_uri(uri=None, room_number=session.room_number)

        #if session.direction != 'incoming':
        #    room_uri = session.request_uri
        #else:
        '''
        '''
        if session.direction != 'incoming':
            # Clear invited participants mapping
            #room_uri_str = '%s@%s' % (session.local_identity.uri.user, session.local_identity.uri.host)
            #room_uri_str = '%s@%s' % (session.room_number, '192.168.1.2')
            room_uri_str = self.get_room_uri_str(uri=None, room_number=session.room_number)
            d = self.invited_participants_map[room_uri_str]
            d[str(session.remote_identity.uri)] -= 1
            if d[str(session.remote_identity.uri)] == 0:
                del d[str(session.remote_identity.uri)]
            #room_uri = session.local_identity.uri
        '''
        display_name = self.remove_participant(session)

        log.info('remove_session before remove room.length %r', room.length)
        log.info('remove_session for room.sessions %r', room.sessions)
        if (room.length > 1) and (session in room.sessions):
            try:
                room.remove_session(session)
            except Exception as e:
                stacktrace = traceback.format_exc()
                log.error("%s", stacktrace)
                log.error("exception in room.remove_session %s", str(e))

        log.info('remove_session room.length %r', room.length)
        # 2 because the other participant is the music server
        # todo - check why we had to change this to 1 here
        if room.length <= 1:
            # we need to stop the remaining session
            log.info('check terminate all sessions room_data.status %r, room length %d', room_data.status, room.length)
            if (room_data.status != 'on_hold') or (room.length == 0) or ((room.length == 1) and (session in room.sessions)):
                log.info('terminate all sessions room %s', room_number)
                room.terminate_sessions()
                room.stop()
                room_data.status = 'closed'

                # mark all the participants in the room as inactive and
                if room_data.hold_timer != None:
                    room_data.hold_timer.stop()
                    room_data.hold_timer = None
                self.remove_room(room_number)
                NotificationCenter().post_notification('ConferenceUpdated', self,
                                                   NotificationData(room_number=room_number,
                                                                    status='closed'))

        log.info("remove_session check room empty stopping %r, length %r", room.stopping, room.length)
        if not room.stopping and room.empty:
            log.info("remove_session remove_room")
            self.remove_room(room_number)
            room.stop()

        if display_name != '':
            NotificationCenter().post_notification('ConferenceLeave', self,
                                                   NotificationData(room_number=room_number,
                                                                    status=room_data.status,
                                                                    display_name=display_name,
                                                                    is_calltaker=session.is_calltaker,
                                                                    psap_id=psap_id))

    '''
    def add_outgoing_participant(self, display_name, sip_uri, session, is_calltaker=False, is_primary=False):
        self.add_participant(display_name, sip_uri, session, 'out', False, False, is_calltaker, is_primary)
    '''
    def add_outgoing_participant(self, display_name, sip_uri, session, is_calltaker=False, mute_audio=False):
        self.add_participant(display_name, sip_uri, session, 'out', mute_audio, False, is_calltaker)

    def add_incoming_participant(self, display_name, sip_uri, session, is_caller, is_calltaker, mute_audio=False):
        self.add_participant(display_name, sip_uri, session, 'in', mute_audio, is_caller, is_calltaker)

    def add_participant(self, display_name, sip_uri, session, direction, mute_audio, is_caller, is_calltaker=False):
        room_number = session.room_number
        room_data = self.get_room_data(room_number)
        psap_id = room_data.psap_id
        participants = room_data.participants

        participant_data = None
        # check if the participant is on hold
        ''' moved to add_session_to_room
        if room_data.status == 'on_hold':
            if room_data.hold_timer != None:
                room_data.hold_timer.stop()
                room_data.hold_timer = None
            room_data.status = 'active'
            NotificationCenter().post_notification('ConferenceHoldUpdated', self,
                                                   NotificationData(room_number=room_number,
                                                                    calltaker=display_name,
                                                                    on_hold=False))
        '''
        older_sip_uri = None
        for participant in participants.itervalues():
            if participant.is_calltaker and (participant.display_name == display_name):
                participant_data = participants[str(sip_uri)]
                older_sip_uri = str(participant_data.uri)
                log.info("add_participant found existing participant %s", participant.display_name)

        if older_sip_uri is not None:
            del participants[older_sip_uri]

        # check for primary here
        is_primary = False
        primary_calltaker_name, primary_calltaker_data = room_data.primary_calltaker
        if ((primary_calltaker_name is None) or primary_calltaker_data.on_hold) and is_calltaker:
            is_primary = True
        if participant_data is None:
            participant_data = ParticipantData()

        if mute_audio:
            session.mute()

        participant_data.uri = str(sip_uri)
        participant_data.display_name = display_name
        participant_data.session = session
        participant_data.direction = direction
        participant_data.mute = mute_audio
        participant_data.send_audio = True
        participant_data.send_video = True
        participant_data.send_text = True
        participant_data.is_caller = is_caller
        participant_data.is_active = True
        participant_data.is_calltaker = is_calltaker
        participant_data.is_primary = is_primary
        participant_data.on_hold = False
        participants[str(sip_uri)] = participant_data

        NotificationCenter().post_notification('ConferenceParticipantAdded', self,
                                               NotificationData(room_number=room_number,
                                                                direction='in',
                                                                is_calltaker=is_calltaker,
                                                                is_primary=is_primary,
                                                                is_caller=is_caller,
                                                                sip_uri=str(sip_uri),
                                                                mute_audio=mute_audio,
                                                                display_name=display_name,
                                                                psap_id=psap_id))

    def set_new_primary(self, participants, primary_calltaker_uri):
        log.info("inside set_new_primary old primary is %r", primary_calltaker_uri)
        for participant_data in participants.itervalues():
            if participant_data.is_calltaker and participant_data.is_active and (str(participant_data.uri) != primary_calltaker_uri):
                log.info("inside set_new_primary new primary is %r", str(participant_data.uri))
                # this is the new primary
                participant_data.is_primary = True
                return True, str(participant_data.uri)

        return False, None

    # this just marks the participant inactive
    def remove_participant(self, session):
        log.info("inside remove_participant")
        room_number = session.room_number
        room_data = self.get_room_data(room_number)
        psap_id = room_data.psap_id
        display_name = ''
        log.info('room_data is %r', room_data)
        log.info('session is %r', session)
        log.info('session is calltaker %r', session.is_calltaker)
        log.info('room_data.participants is %r', room_data.participants)
        log.info('room_data.participants length is %r', len(room_data.participants))
        for participant_data in room_data.participants.itervalues():
            log.info('participant_data is %s', str(participant_data))

        for participant_data in room_data.participants.itervalues():
            log.info('participant_data is %r', participant_data)
            if (participant_data.session == session) and (not participant_data.on_hold):
                participant_data.is_active = False
                participant_data.on_hold=False
                display_name = participant_data.display_name
                if participant_data.is_calltaker:
                    if participant_data.is_primary:
                        log.info('remove_participant found primary calltaker is %r', participant_data.display_name)
                        (has_new_primary, new_primary_uri) = self.set_new_primary(participants=room_data.participants, primary_calltaker_uri=str(participant_data.uri))
                        if has_new_primary:
                            participant_data.is_primary = False
                            NotificationCenter().post_notification('ConferenceParticipantNewPrimary', self,
                                                                   NotificationData(room_number=room_number,
                                                                                    old_primary_uri=str(participant_data.uri),
                                                                                    new_primary_uri=str(new_primary_uri,
                                                                                    psap_id=psap_id)))
                            # in this case we need to mark the old primary as available
                            #reactor.callLater(1, self.set_calltaker_available, username=participant_data.display_name)
                            self.set_calltaker_available(username=participant_data.display_name)
                    else:
                        #reactor.callLater(1, self.set_calltaker_available, username=participant_data.display_name)
                        self.set_calltaker_available(username=participant_data.display_name)

                NotificationCenter().post_notification('ConferenceParticipantRemoved', self,
                                                       NotificationData(room_number=room_number,
                                                                        display_name = participant_data.display_name,
                                                                        sip_uri=str(participant_data.uri)))

            #if (participant_data.session == session) and participant_data.on_hold and participant_data.is_calltaker:
            #    reactor.callLater(1, self.set_calltaker_available, username=participant_data.display_name)

        return display_name


    def add_session_to_room(self, room_number, session, sdp_passthrough=False):
        # Keep track of the invited participants, we must skip ACL policy
        # for SUBSCRIBE requests
        log.info(u'add_session_to_room for Room %s - session %s' % (room_number, session.remote_identity.uri))
        '''
        d = self.invited_participants_map.setdefault(room_uri_str, {})
        d.setdefault(str(session.remote_identity.uri), 0)
        d[str(session.remote_identity.uri)] += 1
        '''
        NotificationCenter().add_observer(self, sender=session)
        room = self.get_room(room_number)
        log.info(u'Room %s - call room.start' % (room_number))
        if not sdp_passthrough:
            room.start()
            log.info(u'Room %s - call room.add_session' % (room_number))
            room.add_session(session)
        log.info(u'Room %s - outgoing session to %s returning' % (room_number, session.remote_identity.uri))
        # new code
        room_data = self.get_room_data(room_number)
        psap_id = room_data.psap_id
        if not room_data.is_call_active:
            if room_data.is_call_on_hold:
                if room_data.hold_timer != None:
                    room_data.hold_timer.stop()
                    room_data.hold_timer = None
                room_data.status = 'active'
                #for participant in room_data.participants.itervalues():
                #    if participant.is_calltaker
                #        participant.on_hold = False
                NotificationCenter().post_notification('ConferenceHoldUpdated', self,
                                                       NotificationData(room_number=room_number,
                                                                        calltaker=session.calltaker_name,
                                                                        on_hold=False,
                                                                        psap_id=psap_id))
            else:
                calltakers = room_data.calltakers
                log.info('add_session_to_room send active notification to calltakers %s', calltakers)
                room_data.status = 'active'
                NotificationCenter().post_notification('ConferenceActive', self,
                                                       NotificationData(room_number=room_number, calltakers=calltakers))
                (display_name, uri, is_calltaker) = self.get_room_caller(room_number)
                if (display_name is not None) and is_calltaker:
                    publish_outgoing_call_status(room_number, display_name, 'active')
        else:
            # if the outgoing call was for a calltaker send active status notification
            if session.is_calltaker:
                publish_active_call(session.calltaker_name, room_number)

    def put_calltaker_on_hold(self, room_number, calltaker_name):
        try:
            log.info('inside put_calltaker_on_hold for room %s, calltaker %s', room_number, calltaker_name)
            calltaker_participant = self._get_calltaker_participant(room_number, calltaker_name)
            if calltaker_participant is None:
                raise ValueError("invalid calltaker %r for room %r" % (calltaker_name, room_number))
            if calltaker_participant.on_hold:
                return
            calltaker_participant.is_active = False
            calltaker_participant.on_hold = True
            room = self.get_room(room_number)
            room_data = self.get_room_data(room_number)
            psap_id = room_data.psap_id
            #todo - finish this
            if room_data.status == 'active':
                # check if there is only 2 sessions in the call
                if len(room.sessions) <= 2:
                    def hold_timer_cb(room_number):
                        hold_timer_cb.duration = hold_timer_cb.duration + 1
                        publish_update_call_timer(psap_id, room_number, 'hold', hold_timer_cb.duration)

                    hold_timer_cb.duration = 0
                    hold_timer = task.LoopingCall(hold_timer_cb, room_number)
                    hold_timer.start(1)  # call every seconds
                    room.play_beep()
                    room_data.status = 'on_hold'
                    room_data.hold_timer = hold_timer
                    NotificationCenter().post_notification('ConferenceHoldUpdated', self,
                                                           NotificationData(room_number=room_number,
                                                                            calltaker=calltaker_name,
                                                                            on_hold=True,
                                                                            psap_id=psap_id))
                else:
                    (has_new_primary, new_primary_uri) = self.set_new_primary(participants=room_data.participants,
                                                                              primary_calltaker_uri=str(
                                                                                  calltaker_participant.uri))
                    if has_new_primary:
                        calltaker_participant.is_primary = False
                        NotificationCenter().post_notification('ConferenceParticipantNewPrimary', self,
                                                               NotificationData(room_number=room_number,
                                                                                old_primary_uri=str(
                                                                                calltaker_participant.uri),
                                                                                new_primary_uri=str(new_primary_uri),
                                                                                psap_id=psap_id))
                    NotificationCenter().post_notification('ConferenceParticipantHoldUpdated', self,
                                                           NotificationData(room_number=room_number,
                                                                            calltaker=calltaker_name,
                                                                            on_hold=True,
                                                                            psap_id=psap_id))

            calltaker_participant.session.end()
            self.set_calltaker_available(username=calltaker_name)
            #room.remove_session(calltaker_participant.session)
        except Exception as e:
            stacktrace = traceback.format_exc()
            log.error("error in put_calltaker_on_hold %s", str(e))
            log.error("%s", stacktrace)

    def mute_calltaker(self, room_number, name, muted):
        participant = self._get_calltaker_participant(room_number, name)
        if participant is None:
            raise ValueError("invalid calltaker %r for room %r" % (name, room_number))
        room_data = self.get_room_data(room_number)
        if room_data is None:
            raise ValueError('conference %s not active or does not exist' % room_number)
        psap_id = room_data.psap_id
        if participant.session is not None:
            if muted:
                participant.session.mute()
            else:
                participant.session.unmute()

        data = NotificationData(room_number=room_number, sip_uri=participant.uri, muted=muted, psap_id=psap_id)
        NotificationCenter().post_notification('ConferenceMuteUpdated', '', data)

        '''
        participant_db_obj = ConferenceParticipant.objects(room_number=room_number, sip_uri=sip_uri)
        set_db_obj_from_request(log, participant_db_obj, request)
        participant_db_obj.save()

        data = NotificationData(room_number=room_number)
        copy_request_data_to_object(request, data)
        NotificationCenter().post_notification('ConferenceParticipantDBUpdated', '', data)
        '''

    def mute_all(self, room_number, muted):
        room_data = self.get_room_data(room_number)
        if room_data is None:
            raise ValueError('conference %s not active or does not exist' % room_number)
        psap_id = room_data.psap_id
        if room_data.incoming_session is not None:
            if muted:
                room_data.incoming_session.mute()
            else:
                room_data.incoming_session.unmute()
        for participant in room_data.participants.itervalues():
            if participant.session is not None:
                if muted:
                    participant.session.mute()
                else:
                    participant.session.unmute()
        data = NotificationData(room_number=room_number, muted=muted, psap_id=psap_id)
        NotificationCenter().post_notification('ConferenceMuteAllUpdated', '', data)

    def mute_user(self, room_number, sip_uri, muted):
        room_data = self.get_room_data(room_number)
        psap_id = room_data.psap_id
        participant = room_data.participants[str(sip_uri)]
        if participant is None:
            raise ValueError("invalid participant %r for room %r" % (sip_uri, room_number))
        if participant.session is not None:
            if muted:
                participant.session.mute()
            else:
                participant.session.unmute()

        data = NotificationData(room_number=room_number, sip_uri=participant.uri, muted=muted, psap_id=psap_id)
        NotificationCenter().post_notification('ConferenceMuteUpdated', '', data)

    def enable_tty(self, room_number):
        log.info('enable_tty for room %r', room_number)
        try:
            room = self.get_room(room_number)
        except RoomNotFoundError:
            log.info('in enable_tty RoomNotFoundError')
            return
        room_data = self.get_room_data(room_number)
        psap_id = room_data.psap_id
        if room_data.has_text:
            return
        if not ServerConfig.tty_enabled:
            room.start_tty()
        room_data.has_tty = True

        data = NotificationData(room_number=room_number, psap_id=psap_id)
        NotificationCenter().post_notification('ConferenceTTYEnabled', '', data)

    def send_tty(self, room_number, tty_text):
        log.info('send_tty for room %r, data %s', room_number, tty_text)
        try:
            room = self.get_room(room_number)
        except RoomNotFoundError:
            log.info('in send_tty RoomNotFoundError')
            return
        room_data = self.get_room_data(room_number)
        if tty_text == 'Enter':
            room_data.tty_text = '{}<CRLF>'.format(room_data.tty_text)
            asciiText = '\x0d' + '\x0a'
            room.sendTtyText(asciiText)
        elif tty_text == 'Backspace':
            room_data.tty_text = room_data.tty_text[:-1]
            asciiText = '\x08'
            room.sendTtyText(asciiText)
        else:
            tty_text = tty_text.lower()
            room.sendTtyText(tty_text)
            room_data.tty_text = '{}{}'.format(room_data.tty_text, tty_text)
        data = NotificationData(room_number=room_number, tty_text=room_data.tty_text)
        NotificationCenter().post_notification('ConferenceTTYUpdated', '', data)
        return room_data.tty_text

    def recvd_tty(self, room_number, tty_char):
        log.info("recvd tty %r, %r", room_number, tty_char)
        tty_char = chr(tty_char)
        if (tty_char is None) or len(tty_char) == 0:
            log.error("empoty tty chat for room %r", room_number)
            return
        hex_char = tty_char[0].encode('hex')
        try:
            room = self.get_room(room_number)
        except RoomNotFoundError:
            log.info('in send_tty RoomNotFoundError')
            return
        room_data = self.get_room_data(room_number)
        psap_id = room_data.psap_id

        if hex_char == '0d' or hex_char == '0a':
            log.debug("last_tty_chars for room %r is %r", room_number, room_data.last_tty_0d)
            if room_data.last_tty_0d:
                room_data.last_tty_0d = False
                room_data.tty_text = room_data.tty_text + "<CRLF>"
            else:
                room_data.last_tty_0d = True
        elif hex_char == '08':  # backspace handling
            # remove last character only if its uppercase as it will be received char
            # received chars are shown in upper case and sent in lower case
            if room_data.tty_text[-1:].isupper():
                room_data.tty_text = room_data.tty_text[:-1]
        else:
            tty_text = tty_char.upper()
            room_data.tty_text = '{}{}'.format(room_data.tty_text, tty_text)
        if not room_data.has_tty:
            room_data.has_tty = True
            data = NotificationData(room_number=room_number, psap_id=psap_id)
            NotificationCenter().post_notification('ConferenceTTYEnabled', '', data)

        data = NotificationData(room_number=room_number, tty_text=room_data.tty_text)
        NotificationCenter().post_notification('ConferenceTTYUpdated', '', data)

    # this is done by participant joining the call again
    #def remove_calltaker_on_hold(self, room_number, calltaker_name):
    #    participant = self._get_calltaker_participant(room_number, calltaker_name)
    #    participant.on_hold = False


    def _get_calltaker_participant(self, room_number, calltaker_name):
        room_data = self.get_room_data(room_number)
        if room_data is None:
            raise ValueError('conference %s not active or does not exist' % room_number)
        for participant in room_data.participants.itervalues():
            if participant.is_calltaker and participant.display_name == calltaker_name:
                return participant
        return None

    def set_calltaker_busy(self, username=None, user_id=None):
        log.info('set_calltaker_busy for username %r, user_id %r', username, user_id)
        self.set_calltaker_status(user_id=user_id, username=username, status='busy')

    def set_calltaker_available(self, username=None, user_id=None):
        log.info('set_calltaker_available for username %r, user_id %r', username, user_id)
        self.set_calltaker_status(user_id=user_id, username=username, status='available')

    def set_calltaker_status(self, username=None, user_id=None, status='available'):
        log.info('psap set_calltaker_status for status %r, username %r, user_id %r', status, username, user_id)
        update_calltaker_status(status, username=username, user_id=user_id)
        '''
        publish_update_calltaker_status(user_id, username, status)
        notification_data = NotificationData(username=username, \
                                             status=status, \
                                             user_id=user_id)
        NotificationCenter().post_notification('CalltakerStatusUpdate', self, notification_data)
        '''
        calltaker_data = CalltakerData()
        if user_id is None:
            calltaker_db_obj = get_calltaker_user(username)
            user_id = str(calltaker_db_obj.user_id)
        log.info("set_calltaker_status user_id %r, username %r, status %r", user_id, username, status)
        calltaker_data.update_status(user_id, status)

    '''
    def remove_participant(self, participant_uri, room_uri):
        try:
            room = self.get_room(room_uri)
        except RoomNotFoundError:
            pass
        else:
            log.info('Room %s - %s removed from conference' % (room_uri, participant_uri))
            room.terminate_sessions(participant_uri)
    '''

    def handle_notification(self, notification):
        handler = getattr(self, '_NH_%s' % notification.name, Null)
        handler(notification)

    def get_oldest_call_with_status(self, status, username):
        filtered_calls = [(room_number, room_data) for room_number, room_data in self._rooms.iteritems() if (room_data.status == status) and (username not in room_data.ignore_calltakers)]
        if len(filtered_calls) > 0:
            (room_number, room_data) = min(filtered_calls, key=lambda call:call[1].start_timestamp)
            return (room_number, room_data)
        return (None, None)

    def send_msrp_text(self, room_number, sender, text):
        log.debug("sendText %r", text)
        room_data = self.get_room_data(room_number)
        psap_id = room_data.psap_id
        chat_stream = room_data.chat_stream
        if chat_stream is not None:
            chat_stream.send_message(text)
        else:
            log.error("no chat stream found for conf %r, sender %r, txtMessage %r", room_number, sender, text)
        sender_uri = room_data.get_calltaker_uri(sender)
        message_id = str(bson.ObjectId())
        data = NotificationData(room_number=room_number, sender_uri=sender_uri, message=text, \
                                message_id=message_id, psap_id=psap_id, content_type="text/plain")
        NotificationCenter().post_notification('ConferenceMSRPText', '', data)
        return message_id, sender_uri

    def _NH_ChatStreamGotMessage(self, notification):
        log.debug("inside _NH_ChatStreamGotMessage")
        if not notification.data.message.content_type.startswith("text/"):
            return
        #remote_identity = notification.data.message.sender.display_name or notification.data.message.sender.uri
        #remote_identity = notification.data.message.sender.uri
        #remoteDisplayName = notification.data.message.sender.display_name
        #if not remoteDisplayName:
        #    remoteUri = notification.data.message.sender.uri
        #    remoteDisplayName = remoteUri.user
        doc = html.fromstring(notification.data.message.content)
        if doc.body.text is not None:
            doc.body.text = doc.body.text.lstrip('\n')
        for br in doc.xpath('.//br'):
            br.tail = '\n' + (br.tail or '')
        '''
        head = RichText('%s> ' % remote_identity, foreground='blue')
        ui = UI()
        ui.writelines([head + line for line in doc.body.text_content().splitlines()])
        '''
        stream = notification.sender
        room_number = stream.room_number
        room_data = self.get_room_data(room_number)
        psap_id = room_data.psap_id
        caller_uri = room_data.caller_uri
        msrp_text = notification.data.message.content
        content_type = notification.data.message.content_type
        #ignore OTR messages
        if msrp_text.startswith('?OTRv3?'):
            return
        log.debug("recvd chatStreamMessage %r", notification.data.message.content)
        message_id = str(bson.ObjectId())
        data = NotificationData(room_number=room_number, sender_uri=caller_uri, message_id=message_id, \
                                message=msrp_text, psap_id=psap_id, content_type=content_type)
        NotificationCenter().post_notification('ConferenceMSRPText', '', data)

        #if self.conf:
        #    self.conf.receivedMsrpMessage(remoteDisplayName, notification.data.message.content)

    def _NH_TTYReceivedChar(self, notification):
        room_number = notification.data.room_number
        tty_char = notification.data.tty_char
        self.recvd_tty(room_number, tty_char)

    def _NH_HeldLookup(self, notification):
        from ...location import derefLocation
        psap_id = notification.data.psap_id
        geoloc_ref = notification.data.geoloc_ref
        caller_name = notification.data.caller_name
        room_number = notification.data.room_number
        derefLocation(room_number,psap_id, geoloc_ref, caller_name)

    def _NH_CalltakerStatusUpdate(self, notification):
        log.info("incoming _NH_CalltakerStatusUpdate")
        user_id = notification.data.user_id
        status = notification.data.status
        janus_busy = notification.data.janus_busy
        username = notification.data.username
        log.info('user_id is %r, janus_busy  is %r, status is %r', user_id, janus_busy, status)
        if (status == 'available') and not janus_busy:
            # check if there are any queued calls
            # mark calls as queued calls
            (room_number, room_data) = self.get_oldest_call_with_status('ringing_queued', username)
            if room_number is None:
                (room_number, room_data) = self.get_oldest_call_with_status('ringing', username)
                if room_number is None:
                    return

            server = room_data.calltaker_server
            sip_uri = "sip:%s@%s" % (username, server)
            old_status = room_data.status
            if room_data.status != 'ringing':
                room_data.status = 'ringing'
            room_data.ignore_calltakers.append(username)
            log.info("call presented to %s, set room %s to %s", username, room_number, room_data.status)
            self.set_calltaker_busy(user_id=user_id)
            outgoing_call_initializer = OutgoingCallInitializer(target_uri=sip_uri,
                                                                room_uri=self.get_room_uri(room_number),
                                                                caller_identity=room_data.incoming_session.remote_identity,
                                                                is_calltaker=True)
            outgoing_call_initializer.start()
            room_data.outgoing_calls[str(sip_uri)] = outgoing_call_initializer
            if old_status != 'ringing':
                NotificationCenter().post_notification('ConferenceUpdated', self,
                                                       NotificationData(room_number=room_number, status=room_data.status))
            '''
            for room_number in self._rooms:
                room_data = self._rooms[room_number]
                if room_data.status == 'ringing_queued' and (username not in room_data.ignore_calltakers):
                    # send call to this calltaker
                    room_data.status = 'ringing'
                    room_data.ignore_calltakers.append(username)
                    log.info("call presented to %s, set room %s to %s", username, room_number, room_data.status)
                    self.set_calltaker_busy(user_id=user_id)
                    outgoing_call_initializer = OutgoingCallInitializer(target_uri=sip_uri,
                                                                        room_uri=self.get_room_uri(room_number),
                                                                        caller_identity=room_data.incoming_session.remote_identity,
                                                                        is_calltaker=True)
                    outgoing_call_initializer.start()
                    room_data.outgoing_calls[str(sip_uri)] = outgoing_call_initializer
                    NotificationCenter().post_notification('ConferenceUpdated', self,
                                                           NotificationData(room_number=room_number, status=room_data.status))
                    return

            # if no queued calls, check if there are any ringing calls and we are ACD ring_all
            # store ring strategy as part of room data
            for room_number in self._rooms:
                room_data = self._rooms[room_number]
                if (room_data.status == 'ringing') and (room_data.acd_strategy == 'ring_all') and (username not in room_data.ignore_calltakers):
                    room_data.ignore_calltakers.append(username)
                    # send call to this calltaker
                    self.set_calltaker_busy(user_id=user_id)
                    outgoing_call_initializer = OutgoingCallInitializer(target_uri=sip_uri,
                                                                        room_uri=self.get_room_uri(room_number),
                                                                        caller_identity=room_data.incoming_session.remote_identity,
                                                                        is_calltaker=True)
                    outgoing_call_initializer.start()
                    room_data.outgoing_calls[str(sip_uri)] = outgoing_call_initializer
                    return
            '''

    def _NH_ConferenceParticipantDBUpdated(self, notification):
        log.info('inside ConferenceParticipantDBUpdated')
        room_number = notification.data.room_number
        sip_uri = notification.data.sip_uri
        log.info('inside ConferenceParticipantDBUpdated room %r, uri %r', room_number, sip_uri)
        try:
            room_data = self.get_room_data(room_number)
            for participant_data in room_data.participants.itervalues():
                if str(participant_data.uri) == sip_uri:
                    if hasattr(notification.data, 'send_video'):
                        log.info('update send_video')
                        participant_data.send_video = notification.data.send_video
                    if hasattr(notification.data, 'send_text'):
                        log.info('update send_text')
                        participant_data.send_video = notification.data.send_text
                    if hasattr(notification.data, 'send_audio'):
                        log.info('update send_audio')
                        participant_data.send_video = notification.data.send_audio
                    if hasattr(notification.data, 'mute'):
                        log.info('update mute')
                        participant_data.mute = notification.data.mute
                        if participant_data.mute:
                            participant_data.session.mute()
                        else:
                            participant_data.session.unmute()

        except RoomNotFoundError:
            log.error("_NH_ConferenceParticipantDBUpdated room not found %r", room_number)

    def _NH_SIPSessionDidStart(self, notification):
        session = notification.sender
        log.info("PSAP _NH_SIPSessionDidStart %r, state %s", session, session.state)
        thread = threading.current_thread()
        log.info("thred is %r", thread)
        log.info("thred ident is %r", thread.ident)

        # for msrp chat we do not do this
        room_data = self.get_room_data(session.room_number)
        sdp_passthrough = False
        if session != None and hasattr(session, 'is_sdp_passthrough') and session.is_sdp_passthrough:
            sdp_passthrough = True
        self.add_session_to_room(session.room_number, session, sdp_passthrough)
        send_call_active_notification(self, session)

        '''
        incoming_session = room_data.incoming_session
        #video_streams = [stream for stream in incoming_session.streams if stream.type == 'video']

        caller_local = None
        caller_remote = None
        calltaker_local = None
        calltaker_remote = None

        log.info("")
        log.info("")
        log.info("=========== incoming_session video streams =============== ")
        for video_stream in video_streams:
            log.info("video_stream is %r ", video_stream)
            log.info("video_stream props are %r ", dir(video_stream))
            log.info("video_stream.producer is %r ", video_stream.producer)
            log.info("video_stream.producer props are %r ", dir(video_stream.producer))
            log.info("video_stream.device is %r ", video_stream.device)
            log.info("video_stream.device props are %r ", dir(video_stream.device))
            log.info("video_stream._transport is %r ", video_stream._transport)
            log.info("video_stream._transport props are %r ", dir(video_stream._transport))
            remote_video = video_stream._transport.remote_video
            local_video = video_stream._transport.local_video
            log.info("remote_video is %r ", remote_video)
            log.info("remote_video props are  %r ", dir(remote_video))
            log.info("remote_video.consumers is %r ", remote_video.consumers)
            log.info("remote_video.closed is %r ", remote_video.closed)
            log.info("local_video is %r ", local_video)
            log.info("local_video props are  %r ", dir(local_video))
            log.info("local_video.producer is %r ", local_video.producer)
            log.info("local_video.closed is %r ", local_video.closed)
            local_video.producer = None
            caller_local = local_video
            caller_remote = remote_video
        log.info("")
        log.info("")
        #video_stream = video_streams[0] if video_streams else None
        calltaker_video_streams = room_data.calltaker_video_streams
        log.info("=========== calltaker video streams =============== ")
        for video_stream in calltaker_video_streams:
            log.info("video_stream is %r ", video_stream)
            log.info("video_stream props are %r ", dir(video_stream))
            log.info("video_stream.producer is %r ", video_stream.producer)
            log.info("video_stream.producer props are %r ", dir(video_stream.producer))
            log.info("video_stream.device is %r ", video_stream.device)
            log.info("video_stream.device props are %r ", dir(video_stream.device))
            log.info("video_stream._transport is %r ", video_stream._transport)
            log.info("video_stream._transport props are %r ", dir(video_stream._transport))
            remote_video = video_stream._transport.remote_video
            local_video = video_stream._transport.local_video
            log.info("remote_video is %r ", remote_video)
            log.info("remote_video props are  %r ", dir(remote_video))
            log.info("remote_video.consumers is %r ", remote_video.consumers)
            log.info("remote_video.closed is %r ", remote_video.closed)
            log.info("local_video is %r ", local_video)
            log.info("local_video props are  %r ", dir(local_video))
            log.info("local_video.producer is %r ", local_video.producer)
            log.info("local_video.closed is %r ", local_video.closed)
            local_video.producer = None
            calltaker_local = local_video
            calltaker_remote = remote_video
        log.info("")
        log.info("")
        if  caller_local != None and \
            calltaker_remote != None:
            log.info("do connect")
            log.info("do create caller_video_connector")
            #log.info("do create caller_video_connector producer port %r", caller_remote.producer_port)
            #log.info("do create caller_video_connector consumer port %r", calltaker_local.consumer_port)
            #caller_video_connector = VideoConnector(caller_remote, calltaker_local)
            log.info("caller_video_connector created")
            caller_local.producer = calltaker_remote
            log.info("do connect done")
        if caller_remote != None and \
            calltaker_local != None:
            log.info("do connect")
            calltaker_local.producer = caller_remote
            log.info("do connect 1")
        video_stream = video_streams[0] if video_streams else None
        calltaker_video_stream = calltaker_video_streams[0] if calltaker_video_streams else None
        '''
        #if video_stream != None and calltaker_video_stream != None:
        #    self.video_conf.add_to_room(session.room_number, calltaker_video_stream)
        #    self.video_conf.add_to_room(session.room_number, video_stream)
        '''
        log.info("check for video producers and consumers video_stream %r", video_stream)
        log.info("video_stream codec %r", video_stream.codec)
        log.info("calltaker_video_stream codec %r", calltaker_video_stream.codec)
        log.info("check for video producers and consumers calltaker_video_stream %r",
                 calltaker_video_stream)
        if video_stream != None and calltaker_video_stream != None:
            log.info("check for video transport %r", video_stream._transport)
            # todo - use a tee to send the incoming video to all participants in future, for now it only goes to one
            if calltaker_video_stream != None and calltaker_video_stream._transport != None \
                    and video_stream != None and video_stream._transport != None:
                log.info("look at adding video producers to consumers")

                log.info("=========== Calltaker video stream =============== ")
                calltaker_video_producer = calltaker_video_stream._transport.remote_video
                calltaker_video_consumer = calltaker_video_stream._transport.local_video

                caller_video_producer = video_stream._transport.remote_video
                caller_video_consumer = video_stream._transport.local_video
                if calltaker_video_producer != None and caller_video_consumer != None:
                    log.info("Add producer to caller video")
                    log.info("caller_video_consumer producer %r", caller_video_consumer.producer)
                    log.info("caller_video_consumer producer consumers %r", caller_video_consumer.producer.consumers)
                    caller_video_consumer.producer.stop()
                    #for consumer in caller_video_consumer.producer.consumers:
                    #    log.info("found consumer %r", consumer)
                    #    caller_video_consumer.producer._remove_consumer(consumer)
                    #    log.info("removed consumer")
                    log.info("calltaker_video_producer %r", calltaker_video_producer)
                    log.info("calltaker_video_producer consumers %r", calltaker_video_producer.consumers)
                    log.info(dir(caller_video_consumer.producer))
                    log.info(dir(calltaker_video_producer))
                    caller_video_consumer.producer = calltaker_video_producer
                #if calltaker_video_consumer != None and caller_video_producer != None:
                #    calltaker_video_consumer.producer = caller_video_producer
                #    log.info("Add producer to calltaker video")

        '''
        '''
        room_number = session.room_number
        room = self.get_room(room_number)
        room.start()
        room.add_session(session)
        '''

    def _NH_SIPSessionWillEnd(self, notification):
        log.info('PSAP got _NH_SIPSessionWillEnd')
        thread = threading.current_thread()
        log.info("thred is %r", thread)
        log.info("thred ident is %r", thread.ident)
        '''
        session = notification.sender
        if hasattr(session, 'room_number') and session.room_number != None:
            room_data = self.get_room_data(session.room_number)
            if room_data != None:
                incoming_session = room_data.incoming_session

                video_streams = [stream for stream in incoming_session.streams if stream.type == 'video']
                caller_local = video_streams[0] if video_streams else None

                calltaker_video_streams = room_data.calltaker_video_streams
                calltaker_local = calltaker_video_streams[0] if calltaker_video_streams else None

                if  caller_local != None:
                    log.info("do disconnect 1")
                    caller_local.producer = None
                    log.info("do disconnect1 done")
                if calltaker_local != None:
                    log.info("do disconnect 2")
                    calltaker_local.producer = None
                    log.info("do disconnect 2 done")
        '''

    @run_in_green_thread
    def _NH_SIPSessionDidEnd(self, notification):
        log.info('PSAP got _NH_SIPSessionDidEnd')
        # We could get this notifiction even if we didn't get SIPSessionDidStart
        session = notification.sender
        notification.center.remove_observer(self, sender=session)

        room_data = self.get_room_data(session.room_number)

        incoming_session = None
        if hasattr(room_data, 'incoming_session'):
            incoming_session = room_data.incoming_session
        if hasattr(session, 'is_sdp_passthrough') and session.is_sdp_passthrough:
            #session.end()
            if room_data.status != 'closed':
                room_data.status = 'closed'
                if incoming_session != None and session != incoming_session:
                    incoming_session.end()
                if room_data.calltaker_video_session != None and session != room_data.calltaker_video_session:
                    room_data.calltaker_video_session.end()
                NotificationCenter().post_notification('ConferenceUpdated', self,
                                                       NotificationData(room_number=session.room_number,
                                                                        status='closed'))
        else:
            self.remove_session_from_room(session.room_number, session)
        send_call_update_notification(self, session, 'closed')
        '''
        room_number = session.room_number
        try:
            room = self.get_room(room_number)
        except RoomNotFoundError:
            log.info('in _NH_SIPSessionDidEnd RoomNotFoundError')
            return
        room_data = self.get_room_data(room_number)

        if not room.started:
            if session == room_data.incoming_session:
                self.end_ringing_call(room_number)
                # add event that the user cancelled

            return

        if session in room.sessions:
            room.remove_session(session)

        # 2 because the other participant is the music server
        if room.length == 2:
            # we need to stop the remaining session
            log.info('terminate all sessions')
            room.terminate_sessions()

        if not room.stopping and room.empty:
            self.remove_room(room_number)
            room.stop()
        '''

    @run_in_green_thread
    def _NH_SIPSessionDidFail(self, notification):
        session = notification.sender
        if hasattr(session, 'room_number') and session.room_number != None:
            room_number = session.room_number
            room_data = self.get_room_data(room_number)
            psap_id = room_data.psap_id
            notification.center.remove_observer(self, sender=session)
            log.info('PSAP Session from %s failed: %s' % (session.remote_identity.uri, notification.data.reason))
            log.info('notification.data: %r' % (notification.data))
            room_data = self.get_room_data(session.room_number)
            self.remove_session_from_room(session.room_number, session)
            if int(notification.data.code) == 487:
                # the caller cancelled the call
                is_calltaker = False
                if hasattr(session, 'is_calltaker'):
                    is_calltaker = session.is_calltaker
                NotificationCenter().post_notification('ConferenceLeave', self,
                                                       NotificationData(room_number=session.room_number,
                                                                        status=room_data.status,
                                                                        display_name=str(session.remote_identity.uri.user),
                                                                        is_calltaker=is_calltaker,
                                                                        psap_id=psap_id))

            send_call_failed_notification(self, session=session, failure_code=notification.data.code, failure_reason=notification.data.reason)

    def transfer_caller(self, room_number, target):
        try:
            from ...db.psap import get_psap_name
            log.info("transfer_caller to %r", target)
            room_data = self.get_room_data(room_number)
            target_uri = SIPURI.parse(target)
            psap_name = get_psap_name(room_data.psap_id)
            extra_headers = []
            extra_headers.append(Header('X-Emergent-Reason', str("Transferred call from %s" % psap_name)))
            room_data.incoming_session.transfer(target_uri, extra_headers=extra_headers)
            log.info("transfer_caller done")
        except:
            stacktrace = traceback.format_exc()
            log.error("transfer_caller error")
            log.error(stacktrace)


class OldOutgoingCallInitializer(object):
    implements(IObserver)

    def __init__(self, target, audio=False, chat=False, room_number=None, user=None, app=None, is_calltaker=False):
        log.info("OutgoingCallInitializer user is %r", user)
        self.app = app
        self.account = get_user_account(user)
        self.user = user
        self.target = target
        self.streams = []
        if audio:
            self.streams.append(MediaStreamRegistry.AudioStream())
        if chat:
            self.streams.append(MediaStreamRegistry.ChatStream())
        self.wave_ringtone = None
        self.room_number = room_number
        self.outgoing_session = None
        # we set it to true in case we need to cancel the session before look up succeeds
        self.cancel = False
        self.is_calltaker = is_calltaker

    def start(self):
        if '@' not in self.target:
            self.target = '%s@%s' % (self.target, self.account.id.domain)
        if not self.target.startswith('sip:') and not self.target.startswith('sips:'):
            self.target = 'sip:' + self.target
        try:
            self.target = SIPURI.parse(self.target)
        except SIPCoreError:
            log.info('Illegal SIP URI: %s' % self.target)
        else:
            if '.' not in self.target.host:
                self.target.host = '%s.%s' % (self.target.host, self.account.id.domain)
            lookup = DNSLookup()
            notification_center = NotificationCenter()
            notification_center.add_observer(self, sender=lookup)
            settings = SIPSimpleSettings()
            if isinstance(self.account, Account) and self.account.sip.outbound_proxy is not None:
                uri = SIPURI(host=self.account.sip.outbound_proxy.host, port=self.account.sip.outbound_proxy.port, parameters={'transport': self.account.sip.outbound_proxy.transport})
            elif isinstance(self.account, Account) and self.account.sip.always_use_my_proxy:
                uri = SIPURI(host=self.account.id.domain)
            else:
                uri = self.target
            lookup.lookup_sip_proxy(uri, settings.sip.transport_list)

    def cancelCall(self):
        self.cancel = True
        if self.outgoing_session is not None:
            # todo add event sending here
            self.outgoing_session.end()
            send_call_update_notification(self, self.outgoing_session, 'cancel')

    def handle_notification(self, notification):
        handler = getattr(self, '_NH_%s' % notification.name, Null)
        handler(notification)

    def _NH_DNSLookupDidSucceed(self, notification):
        notification_center = NotificationCenter()
        notification_center.remove_observer(self, sender=notification.sender)
        if self.cancel:
            return

        session = Session(self.account)
        session.room_number = self.room_number
        notification_center.add_observer(self, sender=session)

        route = notification.data.result[0]

        from_header = FromHeader(SIPURI.new(self.account.uri))
        to_header = ToHeader(SIPURI.new(self.target))
        extra_headers = []

        session.connect(from_header, to_header, route=route, streams=self.streams, is_focus=True,
                             extra_headers=extra_headers)

        '''
        session.connect(ToHeader(self.target), routes=notification.data.result, streams=self.streams)
        #application = SIPSessionApplication()
        #application.outgoing_session = session
        #self.app.outgoing_session = session
        '''
        self.outgoing_session = session
        log.info("remote_identity is %r", session.remote_identity)


    def _NH_DNSLookupDidFail(self, notification):
        log.info('Call to %s failed: DNS lookup error: %s' % (self.target, notification.data.error))
        notification_center = NotificationCenter()
        notification_center.remove_observer(self, sender=notification.sender)
        self.app.outgoing_session_lookup_failed(self.room_number, self.target)

    def _NH_SIPSessionNewOutgoing(self, notification):
        log.info('OutgoingCallInitializer got _NH_SIPSessionNewOutgoing')
        session = notification.sender
        '''
        local_identity = str(session.local_identity.uri)
        if session.local_identity.display_name:
            local_identity = '"%s" <%s>' % (session.local_identity.display_name, local_identity)
        remote_identity = str(session.remote_identity.uri)
        if session.remote_identity.display_name:
            remote_identity = '"%s" <%s>' % (session.remote_identity.display_name, remote_identity)
        log.info("Initiating SIP session from '%s' to '%s' via %s..." % (local_identity, remote_identity, session.route))
        '''
        send_call_update_notification(self, session, 'init')

    def _NH_SIPSessionGotRingIndication(self, notification):
        log.info('OutgoingCallInitializer got _NH_SIPSessionGotRingIndication')
        session = notification.sender
        '''
        local_identity = str(session.local_identity.uri)
        if session.local_identity.display_name:
            local_identity = '"%s" <%s>' % (session.local_identity.display_name, local_identity)
        remote_identity = str(session.remote_identity.uri)
        if session.remote_identity.display_name:
            remote_identity = '"%s" <%s>' % (session.remote_identity.display_name, remote_identity)
        log.info("Initiating SIP session from '%s' to '%s' via %s..." % (local_identity, remote_identity, session.route))
        '''
        send_call_update_notification(self, session, 'ringing')

    '''
    def _NH_SIPSessionGotRingIndication(self, notification):
        settings = SIPSimpleSettings()
        #ui = UI()
        ringtone = settings.sounds.audio_outbound
        
        if ringtone and self.wave_ringtone is None:
            self.wave_ringtone = WavePlayer(SIPApplication.voice_audio_mixer, ringtone.path.normalized, volume=ringtone.volume, loop_count=0, pause_time=2)
            SIPApplication.voice_audio_bridge.add(self.wave_ringtone)
            self.wave_ringtone.start()
        #ui.status = 'Ringing...'

    def _NH_SIPSessionWillStart(self, notification):
        ui = UI()
        if self.wave_ringtone:
            self.wave_ringtone.stop()
            SIPApplication.voice_audio_bridge.remove(self.wave_ringtone)
            self.wave_ringtone = None
        ui.status = 'Connecting...'
    '''
    def _NH_SIPSessionWillStart(self, notification):
        # cancel other invited parties
        if self.app:
            session = notification.sender
            self.app.outgoing_session_will_start(self.target, session)

    def _NH_SIPSessionDidStart(self, notification):
        notification_center = NotificationCenter()
        #ui = UI()
        session = notification.sender
        notification_center.remove_observer(self, sender=session)
        remote_identity = str(session.remote_identity.uri)
        log.info("Session sarted %s, %s" % (remote_identity, session.route))

        log.info('startConference for room %s' % (self.room_number))
        #self.incoming_session.room_number = self.room_number

        log.info(u'_NH_SIPSessionDidStart for session.room_number %s' % session.room_number)
        self.app.outgoing_session_did_start(self.target, self.is_calltaker, session)
        #self.app.add_outgoing_session(session)
        send_call_active_notification(self, session)

        '''
        ui.status = 'Connected'
        reactor.callLater(2, setattr, ui, 'status', None)

        application = SIPSessionApplication()
        application.outgoing_session = None

        for stream in notification.data.streams:
            if stream.type == 'audio':
                send_notice('Audio session established using "%s" codec at %sHz' % (stream.codec, stream.sample_rate))
                if stream.ice_active:
                    send_notice('Audio RTP endpoints %s:%d (ICE type %s) <-> %s:%d (ICE type %s)' % (stream.local_rtp_address,
                                                                                                     stream.local_rtp_port,
                                                                                                     stream.local_rtp_candidate.type.lower(),
                                                                                                     stream.remote_rtp_address,
                                                                                                     stream.remote_rtp_port,
                                                                                                     stream.remote_rtp_candidate.type.lower()))
                else:
                    send_notice('Audio RTP endpoints %s:%d <-> %s:%d' % (stream.local_rtp_address, stream.local_rtp_port, stream.remote_rtp_address, stream.remote_rtp_port))
                if stream.encryption.active:
                    send_notice('RTP audio stream is encrypted using %s (%s)\n' % (stream.encryption.type, stream.encryption.cipher))
        if session.remote_user_agent is not None:
            send_notice('Remote SIP User Agent is "%s"' % session.remote_user_agent)
        '''

    def _NH_SIPSessionDidFail(self, notification):
        notification_center = NotificationCenter()
        session = notification.sender
        notification_center.remove_observer(self, sender=session)
        remote_identity = str(session.remote_identity.uri)
        log.info("Session failed %s, %s" % (remote_identity, session.route))
        self.app.outgoing_session_did_fail(session, self.target, notification.data.code, notification.data.reason)
        send_call_failed_notification(self, session=session, failure_code=notification.data.code, failure_reason=notification.data.reason)

        '''
        ui = UI()
        ui.status = None

        application = SIPSessionApplication()
        application.outgoing_session = None

        if self.wave_ringtone:
            self.wave_ringtone.stop()
            SIPApplication.voice_audio_bridge.remove(self.wave_ringtone)
            self.wave_ringtone = None
        if notification.data.failure_reason == 'user request' and notification.data.code == 487:
            send_notice('SIP session cancelled')
        elif notification.data.failure_reason == 'user request':
            send_notice('SIP session rejected by user (%d %s)' % (notification.data.code, notification.data.reason))
        else:
            send_notice('SIP session failed: %s' % notification.data.failure_reason)
        '''

'''
seems like its not needed

class OutgoingReferInitializer(object):
    implements(IObserver)

    def __init__(self, room_number, room_uri, target_uri, refer_to_uri):
        self.room_number = room_number
        self.target_uri = target_uri
        self.refer_to_uri = refer_to_uri
        self.room_uri = room_uri

    def start(self):
        room_number = self.room_number
        room_data = self.app.get_room_data(room_number)
        psap_id = room_data.psap_id
        self.psap_id = psap_id
        if not self.target_uri.startswith(('sip:', 'sips:')):
            self.target_uri = 'sip:%s' % self.target_uri
        try:
            self.target_uri = SIPURI.parse(self.target_uri)
        except SIPCoreError:
            log.info('OutgoingReferInitializer start Room %s - failed to add %s' % (self.room_uri_str, self.target_uri))
            return
        settings = SIPSimpleSettings()
        lookup = DNSLookup()
        notification_center = NotificationCenter()
        notification_center.add_observer(self, sender=lookup)
        lookup.lookup_sip_proxy(self.target_uri, settings.sip.transport_list)

    def _NH_DNSLookupDidSucceed(self, notification):
        notification_center = NotificationCenter()
        notification_center.remove_observer(self, sender=notification.sender)

        account = DefaultAccount()
        # we use tcp for now, can change later
        transport = 'tcp'
        parameters = {} if transport == 'udp' else {'transport': transport}
        contact_uri = SIPURI(user=account.contact.username, host=SIPConfig.local_ip.normalized,
                             port=getattr(Engine(), '%s_port' % transport), parameters=parameters)
        refer_to_header = ReferToHeader(str(self.refer_to_uri))
        refer_to_header.parameters['method'] = 'INVITE'
        from_header = FromHeader(SIPURI.new(self.room_uri), u'Conference Call')
        referral = Referral(self.target_uri, from_header,
                            ToHeader(self.target_uri),
                            refer_to_header,
                            ContactHeader(contact_uri),
                            account.credentials)
        notification_center.add_observer(self, sender=referral)
        try:
            referral.send_refer(timeout=3)
        except SIPCoreError:
            notification_center.remove_observer(self, sender=referral)
            timeout = 5
            raise ReferralError(error='Internal error')
        self._referral = referral

    def _NH_SIPReferralDidStart(self, notification):
        log.info("inside _NH_SIPReferralDidStart %r", notification)

    def _NH_SIPReferralChangedState(self, notification):
        log.info("inside _NH_SIPReferralChangedState %r", notification)

    def _NH_SIPReferralGotNotify(self, notification):
        log.info("inside _NH_SIPReferralGotNotify %r", notification)

    def _NH_SIPReferralDidEnd(self, notification):
        log.info("inside _NH_SIPReferralDidEnd %r", notification)
        notification_center = NotificationCenter()
        notification_center.remove_observer(self, sender=self._referral)
        self._referral = None

    def _NH_SIPReferralDidFail(self, notification):
        log.info("inside _NH_SIPReferralDidFail")
        notification_center = NotificationCenter()
        notification_center.remove_observer(self, sender=self._referral)
        self._referral = None
        if notification.data.code in (403, 405):
            raise ReferralError(error=sip_status_messages[notification.data.code], code=notification.data.code)
'''


class OutgoingCallInitializer(object):
    implements(IObserver)
    '''
    def __init__(self, target, audio=False, chat=False, room_number=None, user=None, app=None, is_calltaker=False):
        self.app = app

        self.account = get_user_account(user)
        self.user = user
        self.target = target
        self.streams = []
        if audio:
            self.streams.append(MediaStreamRegistry.AudioStream())
        if chat:
            self.streams.append(MediaStreamRegistry.ChatStream())
        self.wave_ringtone = None
        self.room_number = room_number
        self.outgoing_session = None
        # we set it to true in case we need to cancel the session before look up succeeds
        self.cancel = False
        self.is_calltaker = is_calltaker
    '''
    def __init__(self, target_uri, room_uri, caller_identity=None, is_calltaker=False, has_audio=True, has_video=False, has_chat=False, add_failed_event=True, inviting_calltaker=None):
        log.info("OutgoingCallInitializer for target %r, room %r, caller_identity %r, is_calltaker %r", target_uri, room_uri, caller_identity, is_calltaker)
        self.app = PSAPApplication()
        self.caller_identity = caller_identity
        # if this is none we use the caller_identity
        self.inviting_calltaker = inviting_calltaker
        self.room_uri = room_uri
        self.room_uri_str = '%s@%s' % (self.room_uri.user, self.room_uri.host)
        self.room_number = self.room_uri.user
        log.info("OutgoingCallInitializer room_number %r", self.room_number)
        self.target_uri = target_uri
        self.session = None
        self.cancel = False
        self.has_audio = has_audio
        self.has_video = has_video
        self.has_chat = has_chat
        self.streams = []
        self.is_calltaker = is_calltaker
        self.is_ringing = False
        self.calltaker_name = None
        self.ref_id = uuid4().hex
        if is_calltaker:
            calltaker_uri = SIPURI.parse(str(target_uri))
            self.calltaker_name = calltaker_uri.user
        self.add_failed_event = add_failed_event


    def start(self):
        log.info("OutgoingCallInitializer start")
        room_number = self.room_number
        room_data = self.app.get_room_data(room_number)
        psap_id = room_data.psap_id
        if not self.target_uri.startswith(('sip:', 'sips:')):
            self.target_uri = 'sip:%s' % self.target_uri
        try:
            self.target_uri = SIPURI.parse(self.target_uri)
        except SIPCoreError:
            log.info('OutgoingCallInitializer start Room %s - failed to add %s' % (self.room_uri_str, self.target_uri))
            return
        settings = SIPSimpleSettings()
        account = DefaultAccount()
        if account.sip.outbound_proxy is not None:
            uri = SIPURI(host=account.sip.outbound_proxy.host,
                         port=account.sip.outbound_proxy.port,
                         parameters={'transport': account.sip.outbound_proxy.transport})
        else:
            uri = self.target_uri
        lookup = DNSLookup()
        notification_center = NotificationCenter()
        notification_center.add_observer(self, sender=lookup)
        lookup.lookup_sip_proxy(uri, settings.sip.transport_list)

        if room_data.is_call_active:
            NotificationCenter().post_notification('ConferenceOutgoingCall', self,
                                                   NotificationData(room_number=room_number,
                                                                    display_name=str(uri.user),
                                                                    is_calltaker=self.is_calltaker,
                                                                    psap_id=psap_id))

    def cancel_call(self):
        self.cancel = True
        if self.is_calltaker:
            log.info("set user %s available", self.calltaker_name)
            self.app.set_calltaker_available(username=self.calltaker_name)

        if self.session is not None:
            # todo add event sending here
            notification_center = NotificationCenter()
            notification_center.remove_observer(self, sender=self.session)
            self.session.end()
            send_call_update_notification(self, self.session, 'cancel')

    def handle_notification(self, notification):
        handler = getattr(self, '_NH_%s' % notification.name, Null)
        handler(notification)

    def _NH_DNSLookupDidSucceed(self, notification):
        notification_center = NotificationCenter()
        notification_center.remove_observer(self, sender=notification.sender)
        if self.cancel:
            return
        account = DefaultAccount()
        psap_application = PSAPApplication()
        try:
            room_data = psap_application.get_room_data(self.room_number)
        except RoomNotFoundError:
            log.info('_NH_DNSLookupDidSucceed RoomNotFoundError for room %r', self.room_number)
            log.info('_NH_DNSLookupDidSucceed Room %s - failed to add %s' % (self.room_uri_str, self.target_uri))
            return
        '''
        active_media = set(room.active_media).intersection(('audio', 'chat'))
        if not active_media:
            log.info('_NH_DNSLookupDidSucceed no active media')
            log.info('_NH_DNSLookupDidSucceed Room %s - failed to add %s' % (self.room_number, self.target_uri))
            return
        for stream_type in active_media:
            self.streams.append(MediaStreamRegistry.get(stream_type)())
        '''
        incoming_session = room_data.incoming_session
        sdp_val = None
        if incoming_session != None and hasattr(incoming_session, 'is_sdp_passthrough') and incoming_session.is_sdp_passthrough:
            sdp_val = incoming_session.remote_sdp
        if self.has_audio:
            self.streams.append(MediaStreamRegistry.AudioStream())
        if self.has_video:
            self.streams.append(MediaStreamRegistry.VideoStream())
        if self.has_chat:
            self.streams.append(MediaStreamRegistry.ChatStream())

        self.session = Session(account)
        self.session.room_number = self.room_number
        self.session.is_primary = False
        self.session.is_calltaker = self.is_calltaker
        self.session.calltaker_name = self.calltaker_name
        notification_center.add_observer(self, sender=self.session)
        '''
        if self.original_from_header.display_name:
            original_identity = "%s <%s@%s>" % (self.original_from_header.display_name, self.original_from_header.uri.user, self.original_from_header.uri.host)
        else:
            original_identity = "%s@%s" % (self.original_from_header.uri.user, self.original_from_header.uri.host)
        '''
        from_header = FromHeader(SIPURI.new(self.room_uri), u'Conference Call')
        to_header = ToHeader(self.target_uri)
        extra_headers = []
        #if ThorNodeConfig.enabled:
        #    extra_headers.append(Header('Thor-Scope', 'conference-invitation'))
        extra_headers.append(Header('X-Originator-From', str(self.caller_identity)))
        extra_headers.append(SubjectHeader(u'Join conference request from %s' % str(self.caller_identity)))
        route = notification.data.result[0]
        self.session.connect(from_header, to_header, route=route, streams=self.streams, is_focus=True, \
                             extra_headers=extra_headers, sdp_val=sdp_val)

    def _NH_SIPSessionNewOutgoing(self, notification):
        log.info('OutgoingCallInitializer got _NH_SIPSessionNewOutgoing')
        session = notification.sender
        send_call_update_notification(self, session, 'init')

    def _NH_DNSLookupDidFail(self, notification):
        notification_center = NotificationCenter()
        notification_center.remove_observer(self, sender=notification.sender)
        self.app.outgoing_session_lookup_failed(self.room_number, self.target_uri)

    def _NH_SIPSessionGotRingIndication(self, notification):
        log.info("inside _NH_SIPSessionGotRingIndication")
        session = notification.sender
        self.is_ringing = True
        self.app.outgoing_session_is_ringing(self.room_number, self.target_uri)
        send_call_update_notification(self, session, 'ringing')

    def _NH_SIPSessionGotProvisionalResponse(self, notification):
        pass

    def _NH_SIPSessionWillStart(self, notification):
        log.info("_NH_SIPSessionWillStart ")
        # cancel other invited parties
        if self.app:
            session = notification.sender
            self.app.outgoing_session_will_start(self.target_uri, session)

    def _NH_SIPSessionDidStart(self, notification):
        notification.center.remove_observer(self, sender=notification.sender)
        session = notification.sender
        remote_identity = str(session.remote_identity.uri)
        log.info("Session sarted %s, %s" % (remote_identity, session.route))

        log.info('startConference for room %s' % (self.room_number))
        # self.incoming_session.room_number = self.room_number

        log.info(u'_NH_SIPSessionDidStart for session.room_number %s' % session.room_number)
        self.app.outgoing_session_did_start(self.target_uri, self.is_calltaker, session)
        # self.app.add_outgoing_session(session)
        send_call_active_notification(self, session)

        if self.inviting_calltaker is not None:
            publish_outgoing_call_status(self.room_number, self.inviting_calltaker, 'active')

        #psap_application.add_participant(self.session, self.room_uri)
        #log.info('Room %s - %s added %s' % (self.room_uri_str, self._refer_headers.get('From').uri, self.target_uri))
        self.session = None
        self.streams = []

    def _NH_SIPSessionDidFail(self, notification):
        log.info('_NH_SIPSessionDidFail Room %s - failed to add %s: %s' % (self.room_uri_str, self.target_uri, notification.data.reason))
        notification.center.remove_observer(self, sender=notification.sender)
        self.session = None
        self.streams = []
        session = notification.sender
        remote_identity = str(session.remote_identity.uri)
        log.info("Session failed %s, %s" % (remote_identity, session.route))
        self.app.outgoing_session_did_fail(session, self.target_uri, notification.data.code, notification.data.reason, self.add_failed_event)
        if self.inviting_calltaker is not None:
            publish_outgoing_call_status(self.room_number, self.inviting_calltaker, 'failed')
        send_call_failed_notification(self, session=session, failure_code=notification.data.code,
                                      failure_reason=notification.data.reason)

    def _NH_SIPSessionDidEnd(self, notification):
        # If any stream fails to start we won't get SIPSessionDidFail, we'll get here instead
        log.info('Room %s - ended %s' % (self.room_uri_str, self.target_uri))
        notification.center.remove_observer(self, sender=notification.sender)
        self.session = None
        self.streams = []
        session = notification.sender
        self.app.remove_session_from_room(session.room_number, session)
        send_call_update_notification(self, session, 'closed')


class IncomingReferralHandler(object):
    implements(IObserver)

    def __init__(self, refer_request, data):
        self._refer_request = refer_request
        self._refer_headers = data.headers
        self.room_uri = data.request_uri
        self.room_uri_str = '%s@%s' % (self.room_uri.user, self.room_uri.host)
        self.room_number = self.room_uri.user
        self.refer_to_uri = re.sub('<|>', '', data.headers.get('Refer-To').uri)
        self.method = data.headers.get('Refer-To').parameters.get('method', 'INVITE').upper()
        self.session = None
        self.streams = []

    def start(self):
        if not self.refer_to_uri.startswith(('sip:', 'sips:')):
            self.refer_to_uri = 'sip:%s' % self.refer_to_uri
        try:
            self.refer_to_uri = SIPURI.parse(self.refer_to_uri)
        except SIPCoreError:
            log.info('Room %s - failed to add %s' % (self.room_uri_str, self.refer_to_uri))
            self._refer_request.reject(488)
            return
        notification_center = NotificationCenter()
        notification_center.add_observer(self, sender=self._refer_request)
        if self.method == 'INVITE':
            self._refer_request.accept()
            settings = SIPSimpleSettings()
            account = DefaultAccount()
            if account.sip.outbound_proxy is not None:
                uri = SIPURI(host=account.sip.outbound_proxy.host,
                             port=account.sip.outbound_proxy.port,
                             parameters={'transport': account.sip.outbound_proxy.transport})
            else:
                uri = self.refer_to_uri
            lookup = DNSLookup()
            notification_center.add_observer(self, sender=lookup)
            lookup.lookup_sip_proxy(uri, settings.sip.transport_list)
        elif self.method == 'BYE':
            log.info('Room %s - %s removed %s from the room' % (self.room_uri_str, self._refer_headers.get('From').uri, self.refer_to_uri))
            self._refer_request.accept()
            psap_application = PSAPApplication()
            psap_application.remove_participant(self.refer_to_uri, self.room_uri)
            self._refer_request.end(200)
        else:
            self._refer_request.reject(488)

    def handle_notification(self, notification):
        handler = getattr(self, '_NH_%s' % notification.name, Null)
        handler(notification)

    def _NH_DNSLookupDidSucceed(self, notification):
        notification_center = NotificationCenter()
        notification_center.remove_observer(self, sender=notification.sender)
        account = DefaultAccount()
        psap_application = PSAPApplication()
        try:
            room = psap_application.get_room(self.room_number)
        except RoomNotFoundError:
            log.info('Room %s - failed to add %s' % (self.room_uri_str, self.refer_to_uri))
            self._refer_request.end(500)
            return
        active_media = set(room.active_media).intersection(('audio', 'chat'))
        if not active_media:
            log.info('Room %s - failed to add %s' % (self.room_number, self.refer_to_uri))
            self._refer_request.end(500)
            return
        for stream_type in active_media:
            self.streams.append(MediaStreamRegistry.get(stream_type)())
        self.session = Session(account)
        notification_center.add_observer(self, sender=self.session)
        original_from_header = self._refer_headers.get('From')
        if original_from_header.display_name:
            original_identity = "%s <%s@%s>" % (original_from_header.display_name, original_from_header.uri.user, original_from_header.uri.host)
        else:
            original_identity = "%s@%s" % (original_from_header.uri.user, original_from_header.uri.host)
        from_header = FromHeader(SIPURI.new(self.room_uri), u'Conference Call')
        to_header = ToHeader(self.refer_to_uri)
        extra_headers = []
        if self._refer_headers.get('Referred-By', None) is not None:
            extra_headers.append(Header.new(self._refer_headers.get('Referred-By')))
        else:
            extra_headers.append(Header('Referred-By', str(original_from_header.uri)))
        #if ThorNodeConfig.enabled:
        #    extra_headers.append(Header('Thor-Scope', 'conference-invitation'))
        extra_headers.append(Header('X-Originator-From', str(original_from_header.uri)))
        extra_headers.append(SubjectHeader(u'Join conference request from %s' % original_identity))
        route = notification.data.result[0]
        self.session.connect(from_header, to_header, route=route, streams=self.streams, is_focus=True, extra_headers=extra_headers)

    def _NH_DNSLookupDidFail(self, notification):
        notification.center.remove_observer(self, sender=notification.sender)

    def _NH_SIPSessionGotRingIndication(self, notification):
        if self._refer_request is not None:
            self._refer_request.send_notify(180)

    def _NH_SIPSessionGotProvisionalResponse(self, notification):
        if self._refer_request is not None:
            self._refer_request.send_notify(notification.data.code, notification.data.reason)

    def _NH_SIPSessionDidStart(self, notification):
        notification.center.remove_observer(self, sender=notification.sender)
        if self._refer_request is not None:
            self._refer_request.end(200)
        psap_application = PSAPApplication()
        psap_application.add_participant(self.session, self.room_uri)
        log.info('Room %s - %s added %s' % (self.room_uri_str, self._refer_headers.get('From').uri, self.refer_to_uri))
        self.session = None
        self.streams = []

    def _NH_SIPSessionDidFail(self, notification):
        log.info('Room %s - failed to add %s: %s' % (self.room_uri_str, self.refer_to_uri, notification.data.reason))
        notification.center.remove_observer(self, sender=notification.sender)
        if self._refer_request is not None:
            self._refer_request.end(notification.data.code or 500, notification.data.reason or  notification.data.code)
        self.session = None
        self.streams = []

    def _NH_SIPSessionDidEnd(self, notification):
        # If any stream fails to start we won't get SIPSessionDidFail, we'll get here instead
        log.info('Room %s - ended %s' % (self.room_uri_str, self.refer_to_uri))
        notification.center.remove_observer(self, sender=notification.sender)
        if self._refer_request is not None:
            self._refer_request.end(200)
        self.session = None
        self.streams = []

    def _NH_SIPIncomingReferralDidEnd(self, notification):
        notification.center.remove_observer(self, sender=notification.sender)
        self._refer_request = None
