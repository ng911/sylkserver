
from application.notification import IObserver, NotificationCenter, NotificationData
from application.python import Null
from twisted.internet import reactor
from zope.interface import implements

from sipsimple.threading.green import run_in_green_thread
from sylk.applications import SylkApplication, ApplicationLogger
from sipsimple.streams import MediaStreamRegistry
from sipsimple.core import Engine, SIPCoreError, SIPURI, ToHeader, FromHeader
from sipsimple.lookup import DNSLookup
from sipsimple.configuration.settings import SIPSimpleSettings
#from sipsimple.session import IllegalStateError, Session
from sipsimple.session import IllegalStateError
from sylk.session import Session
from sylk.accounts import DefaultAccount, get_user_account
from sipsimple.account import Account
from uuid import uuid4
from collections import namedtuple

from sylk.db.authenticate import authenticate_call
from sylk.db.queue import get_queue_details, get_queue_members
from acd import get_calltakers
from sylk.data.call import CallData
from sylk.configuration import ServerConfig, SIPConfig
from sylk.utils import dump_object_member_vars, dump_object_member_funcs, dump_var
from sylk.notifications.call import send_call_update_notification, send_call_active_notification, send_call_failed_notification
from sylk.applications.psap.room import Room

log = ApplicationLogger(__package__)

class RoomNotFoundError(Exception): pass

class RoomData(object):
    __slots__ = ['room', 'incoming_session', 'call_type', 'direction', 'outgoing_calls', 'invitation_timer', 'participants']
    def __init__(self):
        pass

class ParticipantData(object):
    __slots__ = ['display_name', 'uri', 'session', 'direction', 'mute_audio', 'recv_audio', 'recv_video',
                 'recv_chat', 'is_caller', 'is_active']
    def __init__(self):
        pass

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
        log.info(u'PSAPApplication init')
        CallData()
        #self.invited_parties = {}
        #self.ringing_timer = None
        self._rooms = {}

    def start(self):
        log.info(u'PSAPApplication start')

    def stop(self):
        log.info(u'PSAPApplication stop')

    def get_rooms(self):
        return list(self._rooms.keys())

    def create_room(self, incoming_session, call_type, direction):
        room_number = uuid4().hex
        room = Room(room_number)
        room_data = RoomData()
        room_data.room = room
        room_data.call_type = call_type
        room_data.incoming_session = incoming_session
        room_data.outgoing_calls = {}
        room_data.participants = {}
        room_data.direction = direction

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

    def get_room_uri_str(self, uri=None, room_number=None):
        if room_number is None:
            room_uri = '%s@%s' % (uri.user, uri.host)
        else:
            local_ip = SIPConfig.local_ip.normalized
            room_uri = '%s@%s' % (room_number, local_ip)
        return room_uri

    def get_room_uri(self, uri=None, room_number=None):
        room_uri_str = self.get_room_uri_str(uri, room_number)
        if not room_uri_str.startswith("sip:"):
            room_uri_str = "sip:%s" % room_uri_str
        return SIPURI.parse(room_uri_str)
    '''

    def remove_room(self, room_number):
        self._rooms.pop(room_number, None)

    def incoming_session(self, session):
        log.info(u'New incoming session %s from %s' % (session.call_id, format_identity(session.remote_identity)))
        send_call_update_notification(self, session, 'init')

        has_audio = False
        has_tty = False
        has_text = False
        has_video = False

        audio_streams = [stream for stream in session.proposed_streams if stream.type=='audio']
        chat_streams = [stream for stream in session.proposed_streams if stream.type=='chat']
        if not audio_streams and not chat_streams:
            log.info(u'Session %s rejected: invalid media, only RTP audio and MSRP chat are supported' % session.call_id)
            session.reject(488)
            send_call_update_notification(self, session, 'reject')
            return
        if audio_streams:
            has_audio = True
            session.send_ring_indication()
            send_call_update_notification(self, session, 'ringing')

        if chat_streams:
            has_text = True

        remote_identity = session.remote_identity
        local_identity = session.local_identity
        peer_address = session.peer_address

        rooms = self.get_rooms()

        log.info(u"calling authenticate_call with ip %r, port %r, called_number %r, from_uri %r, rooms %r",
            peer_address.ip, peer_address.port, local_identity.uri.user, remote_identity.uri, rooms)
        # first verify the session
        (authenticated, call_type, data) = authenticate_call(peer_address.ip, peer_address.port, local_identity.uri.user, remote_identity.uri, rooms)

        if not authenticated:
            log.info("call not authenticated, reject it")
            session.reject(403)
            send_call_update_notification(self, session, 'reject')
            return

        NotificationCenter().add_observer(self, sender=session)

        if (call_type == 'sos') or (call_type == 'outgoing'):
            inoming_link = data
            queue_details = get_queue_details(inoming_link.queue_id)
            queue_members = get_queue_members(inoming_link.queue_id)

            if call_type == 'sos':
                calltakers = get_calltakers(queue_details, queue_members)
                server = ServerConfig.asterisk_server
                sip_uris = ["sip:%s@%s" % (calltaker.username, server) for calltaker in calltakers.itervalues()]
                log.info("sip_uris is %r", sip_uris)
            else:
                outgoing_gateway = ServerConfig.outgoing_gateway
                sip_uri = '{}@{}'.format(local_identity.uri.user, outgoing_gateway)
                sip_uris = [sip_uri]

            if call_type == 'outgoing':
                direction = 'out'
                is_calltaker = True
            else:
                direction = 'in'
                is_calltaker = False

            (room_number, room_data) = self.create_room(session, call_type, direction=direction)
            session.room_number = room_number

            self.add_incoming_participant(display_name=remote_identity.uri.user, sip_uri=str(remote_identity.uri), session=session, is_caller=True, is_calltaker=is_calltaker)
            NotificationCenter().post_notification('ConferenceCreated', self,
                                                   NotificationData(room_number=room_number, direction=direction,
                                                                    call_type=call_type, status='ringing',
                                                                    primary_queue_id=inoming_link.queue_id, link_id=inoming_link.link_id,
                                                                    caller_ani=remote_identity.uri.user, caller_uri=str(remote_identity.uri),
                                                                    caller_name=remote_identity.uri.user,
                                                                    has_audio=has_audio, has_text=has_text, has_video=has_video, has_tty=has_tty))

            # start call timer
            ring_time = queue_details.ring_time
            log.info("ringing timeout for conf room %r is %r", room_number, ring_time)

            try:
                ringing_timer = reactor.callLater(ring_time, self.on_ringing_timeout, room_number)
                room_data.invitation_timer = ringing_timer
                log.info("ringing_timer set ")
            except Exception as e:
                log.error("exception in setting ringing_timer %r", e)

            # create the conference room here
            #get_conference_application().incoming_session(self.incoming_session, room_number=room_number)

            for sip_uri in sip_uris:
                log.info("create outgoing call to sip_uri %r", sip_uri)
                # create an outbound session here for calls to calltakers
                outgoing_call_initializer = OutgoingCallInitializer(target=sip_uri,
                                                                   audio=True,
                                                                   room_number=room_number,
                                                                   user=remote_identity.uri.user,
                                                                    app=self,
                                                                    is_calltaker=not is_calltaker)
                outgoing_call_initializer.start()
                room_data.outgoing_calls[sip_uri] = outgoing_call_initializer
                #self.invited_parties[sip_uri] = outgoing_call_initializer
        elif call_type == 'sos_room':
            room_number = local_identity.uri.user
            session.room_number = room_number
            log.info("join call to room %r", room_number)
            self.add_incoming_participant(self, display_name=remote_identity.uri.user, sip_uri=str(remote_identity.uri), session=session, is_caller=False, is_calltaker=True)
            reactor.callLater(0, self.accept_session, session)
        elif call_type == 'admin':
            pass

    def on_ringing_timeout(self, incoming_session, room_number):
        log.info("on_ringing_timeout")
        log.info("timed out ringing for conf room %r", room_number)
        self.end_ringing_call(room_number)
        self.ringing_timer = None
        send_call_update_notification(self, incoming_session, 'abandoned')
        NotificationCenter().post_notification('ConferenceUpdated', self,
                                               NotificationData(room_number=room_number, status='abandoned'))

    def end_ringing_call(self, room_number):
        room = self.get_room(room_number)
        room_data = self.get_room_data(room_number)
        room_data.invitation_timer = None
        if not room.started:
            room_data = self.get_room_data(room_number)
            for outgoing_call_initializer in room_data.outgoing_calls.itervalues():
                outgoing_call_initializer.cancel()
            room_data.incoming_session.end()
            self.remove_room(room_number)
            # todo add more acd handling here
            # todo mark the conference as ended

    def incoming_subscription(self, request, data):
        request.reject(405)

    def incoming_referral(self, request, data):
        request.reject(405)

    def incoming_message(self, request, data):
        request.reject(405)

    def outgoing_session_lookup_failed(self, room_number, sip_uri):
        room_data = self.get_room_data(room_number)
        if room_data is not None:
            if sip_uri in room_data.outgoing_calls:
                # todo send event that the call failed
                #outgoing_call_initializer = room_data.outgoing_calls[sip_uri]
                del room_data.outgoing_calls[sip_uri]

            if len(room_data.outgoing_calls) == 0:
                # todo add handling here, put the call in queue?
                pass

    def outgoing_session_did_fail(self, room_number, sip_uri, failure_code, reason):
        room_data = self.get_room_data(room_number)
        if room_data is not None:
            if sip_uri in room_data.outgoing_calls:
                # todo send event that the call failed
                #outgoing_call_initializer = room_data.outgoing_calls[sip_uri]
                del room_data.outgoing_calls[sip_uri]

            if len(room_data.outgoing_calls) == 0:
                # todo add handling here, put the call in queue?
                pass

    def outgoing_session_will_start(self, sip_uri, session):
        room_number = session.room_number
        room = self.get_room(room_number)
        room_data = self.get_room_data(room_number)

        if not room.started:
            # streams = [stream for stream in (audio_stream, chat_stream, transfer_stream) if stream]
            # reactor.callLater(4 if audio_stream is not None else 0, self.accept_session, session, streams)
            reactor.callLater(0, self.accept_session, room_data.incoming_session)

            if room_data.invitation_timer is not None:
                room_data.invitation_timer.cancel()
                room_data.invitation_timer = None

            for target, outgoing_call_initializer in room_data.outgoing_calls.iteritems():
                if target != sip_uri:
                    outgoing_call_initializer.cancel()
            room_data.outgoing_calls = {}
            self.add_session_to_room(session)
            self.add_outgoing_participant(display_name=sip_uri.user, sip_uri=str(sip_uri), session=session, is_calltaker=self.is_calltaker)
        else:
            session.end()


    def outgoing_session_did_start(self, sip_uri, session):
        pass

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

    def accept_session(self, session):
        if session.state == 'incoming':
            audio_streams = [stream for stream in session.proposed_streams if stream.type == 'audio']
            chat_streams = [stream for stream in session.proposed_streams if stream.type == 'chat']
            audio_stream = audio_streams[0] if audio_streams else None
            chat_stream = chat_streams[0] if chat_streams else None
            streams = [stream for stream in (audio_stream, chat_stream) if stream]
            try:
                session.accept(streams, is_focus=True)
            except IllegalStateError:
                pass

    def remove_session(self, session):
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
        self.remove_participant(session)

        if session in room.sessions:
            room.remove_session(session)

        # 2 because the other participant is the music server
        if room.length == 2:
            # we need to stop the remaining session
            log.info('terminate all sessions')
            room.terminate_sessions()
            NotificationCenter().post_notification('ConferenceUpdated', self,
                                                   NotificationData(room_number=room_number,
                                                                    status='closed'))

        if not room.stopping and room.empty:
            self.remove_room(room_number)
            room.stop()

    '''
    ParticipantData = namedtuple('ParticipantData',
                                 'display_name uri session direction mute_audio recv_audio recv_video recv_chat is_caller is_active')
    '''
    def add_outgoing_participant(self, display_name, sip_uri, session, is_calltaker):
        self.add_participant(display_name, sip_uri, session, 'out', False, False, is_calltaker)

    def add_incoming_participant(self, display_name, sip_uri, session, is_caller, is_calltaker):
        self.add_participant(display_name, sip_uri, session, 'in', False, is_caller, is_calltaker)

    def add_participant(self, display_name, sip_uri, session, direction, mute_audio, is_caller, is_calltaker):
        room_number = session.room_number
        room_data = self.get_room_data(room_number)
        participants = room_data.participants
        participant_data = ParticipantData()
        participant_data.uri = sip_uri
        participant_data.session = session
        participant_data.direction = direction
        participant_data.mute_audio = mute_audio
        participant_data.recv_audio = True
        participant_data.recv_video = False
        participant_data.recv_chat = False
        participant_data.is_caller = is_caller
        participant_data.is_active = True
        participants[sip_uri] = participant_data

        NotificationCenter().post_notification('ConferenceParticipantAdded', self,
                                               NotificationData(room_number=room_number,
                                                                direction='in',
                                                                is_calltaker=is_calltaker,
                                                                is_caller=is_caller,
                                                                sip_uri=str(sip_uri),
                                                                display_name=display_name))

    # this just marks the participant inactive
    def remove_participant(self, session):
        room_number = session.room_number
        room_data = self.get_room_data(room_number)
        for sip_uri, participant_data in room_data.participants.itervalues():
            if participant_data.session == session:
                participant_data.is_active = False
                NotificationCenter().post_notification('ConferenceParticipantRemoved', self,
                                                       NotificationData(room_number=room_number,
                                                                        display_name = participant_data.display_name,
                                                                        sip_uri=str(participant_data.uri)))

    def add_session_to_room(self, session):
        # Keep track of the invited participants, we must skip ACL policy
        # for SUBSCRIBE requests
        room_number = session.room_number
        log.info(u'Room %s - outgoing session to %s started' % (room_number, session.remote_identity.uri))
        '''
        d = self.invited_participants_map.setdefault(room_uri_str, {})
        d.setdefault(str(session.remote_identity.uri), 0)
        d[str(session.remote_identity.uri)] += 1
        '''
        NotificationCenter().add_observer(self, sender=session)
        room = self.get_room(room_number)
        room.start()
        room.add_session(session)

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

    def _NH_SIPSessionDidStart(self, notification):
        session = notification.sender
        self.add_session_to_room(session)
        send_call_active_notification(self, session)
        '''
        room_number = session.room_number
        room = self.get_room(room_number)
        room.start()
        room.add_session(session)
        '''

    @run_in_green_thread
    def _NH_SIPSessionDidEnd(self, notification):
        log.info('got _NH_SIPSessionDidEnd')
        # We could get this notifiction even if we didn't get SIPSessionDidStart
        session = notification.sender
        notification.center.remove_observer(self, sender=session)

        self.remove_session(session)
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

    def _NH_SIPSessionDidFail(self, notification):
        session = notification.sender
        notification.center.remove_observer(self, sender=session)
        log.info(u'Session from %s failed: %s' % (session.remote_identity.uri, notification.data.reason))
        self.remove_session(session)
        send_call_failed_notification(self, session=session, failure_code=notification.data.code, failure_reason=notification.data.reason)


class OutgoingCallInitializer(object):
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

    def cancel(self):
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

        from_header = FromHeader(SIPURI.new(self.account.uri), self.user)
        to_header = ToHeader(SIPURI.new(self.target))
        extra_headers = []

        self.session.connect(from_header, to_header, route=route, streams=self.streams, is_focus=True,
                             extra_headers=extra_headers)

        '''
        session.connect(ToHeader(self.target), routes=notification.data.result, streams=self.streams)
        #application = SIPSessionApplication()
        #application.outgoing_session = session
        #self.app.outgoing_session = session
        '''
        self.outgoing_session = session
        send_call_update_notification(self, session, 'init')

    def _NH_DNSLookupDidFail(self, notification):
        log.info('Call to %s failed: DNS lookup error: %s' % (self.target, notification.data.error))
        notification_center = NotificationCenter()
        notification_center.remove_observer(self, sender=notification.sender)
        self.app.outgoing_session_lookup_failed(self.room_number, self.target)

    def _NH_SIPSessionNewOutgoing(self, notification):
        session = notification.sender
        local_identity = str(session.local_identity.uri)
        if session.local_identity.display_name:
            local_identity = '"%s" <%s>' % (session.local_identity.display_name, local_identity)
        remote_identity = str(session.remote_identity.uri)
        if session.remote_identity.display_name:
            remote_identity = '"%s" <%s>' % (session.remote_identity.display_name, remote_identity)
        log.info("Initiating SIP session from '%s' to '%s' via %s..." % (local_identity, remote_identity, session.route))
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
        self.app.outgoing_session_did_start(self.target, session)
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
        self.app.outgoing_session_did_fail(self.target, session, notification.data.code, notification.data.reason)
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

