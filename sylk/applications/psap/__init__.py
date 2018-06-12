
import re
import traceback
from application.notification import IObserver, NotificationCenter, NotificationData
from application.python import Null
from twisted.internet import reactor
from twisted.internet import task
from zope.interface import implements

from sipsimple.threading.green import run_in_green_thread
from sylk.applications import SylkApplication, ApplicationLogger
from sipsimple.streams import MediaStreamRegistry
from sipsimple.core import Engine, SIPCoreError, SIPURI, ToHeader, FromHeader, Header, SubjectHeader
from sipsimple.lookup import DNSLookup
from sipsimple.configuration.settings import SIPSimpleSettings
from sipsimple.session import IllegalStateError
from sylk.session import Session
from sylk.accounts import get_user_account
from sipsimple.account import Account
from uuid import uuid4

from sylk.accounts import DefaultAccount
from sylk.db.authenticate import authenticate_call
from sylk.db.queue import get_queue_details, get_queue_members
from acd import get_calltakers
from sylk.data.call import CallData
from sylk.data.conference import ConferenceData
from sylk.configuration import ServerConfig, SIPConfig
# from sylk.utils import dump_object_member_vars, dump_object_member_funcs, dump_var
from sylk.notifications.call import send_call_update_notification, send_call_active_notification, send_call_failed_notification
from sylk.applications.psap.room import Room
from sylk.location import ali_lookup
from sylk.wamp import publish_update_call_timer, publish_outgoing_call_status

log = ApplicationLogger(__package__)

class RoomNotFoundError(Exception): pass

class RoomData(object):
    __slots__ = ['room', 'incoming_session', 'call_type', 'direction', 'outgoing_calls', 'invitation_timer', 'ringing_duration_timer', 'duration_timer', 'participants', 'status', 'hold_timer']
    def __init__(self):
        pass

class ParticipantData(object):
    __slots__ = ['display_name', 'uri', 'session', 'direction', 'mute', 'send_audio', 'send_video',
                 'send_text', 'is_caller', 'is_active', 'is_calltaker', 'is_primary', 'on_hold']
    def __init__(self):
        pass

    def __repr__(self):
        return "display_name %r, uri %r, session %r, direction %r, mute %r, send_audio %r, send_video %r, send_text %r, is_caller %r, is_active %r, on_hold %r, is_primary %r" % \
               (self.display_name, self.uri, self.session, self.direction, self.mute, self.send_audio, self.send_video, self.send_text, self.is_caller, self.is_active, self.on_hold, self.is_primary)

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
        ConferenceData()
        self._rooms = {}

    def init_observers(self):
        log.info("ConferenceData init_observers")
        # this one is used to change the mute, or send status of different media streams
        NotificationCenter().add_observer(self, name='ConferenceParticipantDBUpdated')

    def start(self):
        log.info(u'PSAPApplication start')
        self.init_observers()

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
        room_data.invitation_timer = None
        room_data.ringing_duration_timer = None
        room_data.duration_timer = None
        room_data.status = 'init'
        room_data.hold_timer = None

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
            for participant_data in room_data.participants.itervalues():
                if participant_data.is_calltaker:
                    calltakers.append(participant_data.display_name)
        return calltakers

    def get_room_caller(self, room_number):
        if room_number in self._rooms:
            room_data = self._rooms[room_number]
            for participant_data in room_data.participants.itervalues():
                if participant_data.is_caller:
                    return (participant_data.display_name, participant_data.uri, participant_data.is_calltaker)
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
        (authenticated, call_type, incoming_link, calltaker_obj) = authenticate_call(peer_address.ip, peer_address.port, local_identity.uri.user, remote_identity.uri, rooms)

        if not authenticated:
            log.info("call not authenticated, reject it")
            session.reject(403)
            send_call_update_notification(self, session, 'reject')
            return

        NotificationCenter().add_observer(self, sender=session)

        if (call_type == 'sos') or (call_type == 'outgoing') or (call_type == 'outgoing_calltaker'):
            queue_details = None

            if call_type == 'sos':
                queue_details = get_queue_details(incoming_link.queue_id)
                queue_members = get_queue_members(incoming_link.queue_id)
                calltakers = get_calltakers(queue_details, queue_members)
                server = ServerConfig.asterisk_server
                sip_uris = ["sip:%s@%s" % (calltaker.username, server) for calltaker in calltakers.itervalues()]
                log.info("sip_uris is %r", sip_uris)
                forward_to_calltaker=True
            else:
                if call_type == 'outgoing':
                    outgoing_gateway = ServerConfig.outgoing_gateway
                    sip_uri = 'sip:+{}@{}'.format(local_identity.uri.user, outgoing_gateway)
                    sip_uris = [sip_uri]
                    forward_to_calltaker=False
                elif call_type == 'outgoing_calltaker':
                    forward_to_calltaker=True
                    server = ServerConfig.asterisk_server
                    sip_uri = 'sip:{}@{}'.format(local_identity.uri.user, server)
                    sip_uris = [sip_uri]

            if (call_type == 'outgoing') or (call_type == 'outgoing_calltaker'):
                direction = 'out'
                is_call_from_calltaker = True
            else:
                direction = 'in'
                is_call_from_calltaker = False

            (room_number, room_data) = self.create_room(session, call_type, direction=direction)
            session.room_number = room_number

            if (call_type == 'sos') and hasattr(incoming_link, 'ali_format') and (incoming_link.ali_format != ''):
                log.info('inoming_link.ali_format is %r', incoming_link.ali_format)
                lookup_number = remote_identity.uri.user
                # make sure there is no + prefix in the number and it is 10 digits long
                if lookup_number.startswith('+1'):
                    lookup_number = lookup_number[2:]
                elif lookup_number.startswith('1'):
                    lookup_number = lookup_number[1:]
                log.info('calling ali_lookup for room %r, user %r, format %r', room_number, lookup_number, incoming_link.ali_format)
                ali_lookup(room_number, lookup_number, incoming_link.ali_format)

            room_data.status = 'ringing'
            NotificationCenter().post_notification('ConferenceCreated', self,
                                                   NotificationData(room_number=room_number, direction=direction,
                                                                    call_type=call_type, status='ringing',
                                                                    primary_queue_id=incoming_link.queue_id if hasattr(incoming_link, 'queue_id') else None,
                                                                    link_id=incoming_link.link_id,
                                                                    caller_ani=remote_identity.uri.user, caller_uri=str(remote_identity.uri),
                                                                    caller_name=remote_identity.uri.user,
                                                                    has_audio=has_audio, has_text=has_text, has_video=has_video, has_tty=has_tty))

            self.add_incoming_participant(display_name=remote_identity.uri.user, sip_uri=str(remote_identity.uri), session=session, is_caller=True, is_calltaker=is_call_from_calltaker)
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
                    publish_update_call_timer(room_number, 'ringing', ringing_duration_timer_cb.duration)

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

            for sip_uri in sip_uris:
                log.info("create outgoing call to sip_uri %r", sip_uri)
                # create an outbound session here for calls to calltakers
                outgoing_call_initializer = OutgoingCallInitializer(target_uri=sip_uri, room_uri=self.get_room_uri(room_number),
                                                                    caller_identity=session.remote_identity, is_calltaker=forward_to_calltaker)
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
            session.room_number = room_number
            log.info("join call to room %r", room_number)
            self.add_incoming_participant(display_name=remote_identity.uri.user, sip_uri=str(remote_identity.uri), session=session, is_caller=False, is_calltaker=True)
            reactor.callLater(0, self.accept_session, session)
        elif call_type == 'admin':
            pass

    def on_ringing_timeout(self, incoming_session, room_number):
        log.info("on_ringing_timeout")
        log.info("timed out ringing for conf room %r", room_number)

        room = self.get_room(room_number)
        if room and (not room.started):
            room_data = self.get_room_data(room_number)
            room_data.invitation_timer = None
            self.end_ringing_call(room_number)
            if room_data and (room_data.direction == 'out'):
                status = 'timed_out'
            else:
                status = 'abandoned'
            room_data.status = status
            send_call_update_notification(self, incoming_session, status)
            NotificationCenter().post_notification('ConferenceUpdated', self,
                                                   NotificationData(room_number=room_number, status=status))
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
        room_data = self.get_room_data(room_number)
        if room_data is not None:
            if sip_uri in room_data.outgoing_calls:
                # todo send event that the call failed
                #outgoing_call_initializer = room_data.outgoing_calls[sip_uri]
                del room_data.outgoing_calls[str(sip_uri)]

            if len(room_data.outgoing_calls) == 0:
                # todo add handling here, put the call in queue?
                pass

    def outgoing_session_did_fail(self, session, sip_uri, failure_code, reason):
        log.info('outgoing_session_did_fail session %r, sip_uri %r, failure_code %r, reason %r', session, sip_uri, failure_code, reason)
        room_number = session.room_number
        log.info('outgoing_session_did_fail room_number %r', room_number)
        room_data = self.get_room_data(room_number)
        if room_data is not None:
            if str(sip_uri) in room_data.outgoing_calls:
                log.info('found room_data.outgoing_calls ')
                # todo send event that the call failed
                #outgoing_call_initializer = room_data.outgoing_calls[sip_uri]
                del room_data.outgoing_calls[str(sip_uri)]
                if room_data.direction == 'out':
                    (display_name, uri, is_calltaker) = self.get_room_caller(room_number)
                    if (display_name is not None) and is_calltaker:
                        publish_outgoing_call_status(room_number, display_name, 'failed')
            else:
                log.info('not found room_data.outgoing_calls for %r', str(sip_uri))


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

            if session.is_calltaker:
                session.is_primary = True
            if room_data.ringing_duration_timer is not None:
                room_data.ringing_duration_timer.stop()
                room_data.ringing_duration_timer = None
            if room_data.invitation_timer is not None:
                room_data.invitation_timer.cancel()
                room_data.invitation_timer = None
            log.info('room_data.outgoing_calls %r', room_data.outgoing_calls)
            for target, outgoing_call_initializer in room_data.outgoing_calls.iteritems():
                log.info('target %r', target)
                log.info('outgoing_call_initializer %r', outgoing_call_initializer)

                if target != str(sip_uri):
                    outgoing_call_initializer.cancel_call()
            room_data.outgoing_calls = {}

    def outgoing_session_did_start(self, sip_uri, session):
        room_number = session.room_number

        self.add_session_to_room(session)
        #todo - add proper value of is_calltaker
        self.add_outgoing_participant(display_name=sip_uri.user, sip_uri=str(sip_uri), session=session, is_calltaker=True, is_primary=session.is_primary)
        calltakers = self.get_calltakers_in_room(room_number)
        log.info('outgoing_session_did_start send active notification to calltakers %s', calltakers)
        room_data = self.get_room_data(room_number)
        room_data.status = 'active'
        NotificationCenter().post_notification('ConferenceActive', self,
                                               NotificationData(room_number=room_number, calltakers=calltakers))
        (display_name, uri, is_calltaker) = self.get_room_caller(room_number)
        if (display_name is not None) and is_calltaker:
            publish_outgoing_call_status(room_number, display_name, 'active')
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

    def accept_session(self, session):
        if session.state == 'incoming':
            audio_streams = [stream for stream in session.proposed_streams if stream.type == 'audio']
            chat_streams = [stream for stream in session.proposed_streams if stream.type == 'chat']
            audio_stream = audio_streams[0] if audio_streams else None
            chat_stream = chat_streams[0] if chat_streams else None
            streams = [stream for stream in (audio_stream, chat_stream) if stream]
            try:
                log.info("accept incoming session %r", session)
                session.accept(streams, is_focus=True)
            except IllegalStateError:
                pass

    def remove_session(self, session):
        log.info('remove_session for session %r, room_number %r', session, session.room_number)
        room_number = session.room_number
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

        if not room.started:
            log.info('remove_session room not started yet')
            if session == room_data.incoming_session:
                log.info('remove_session room not started yet, end_ringing_call')
                self.end_ringing_call(room_number)
                # add event that the user cancelled

            self.remove_room(room_number)
            room.stop()
            room_data.status = 'closed'
            NotificationCenter().post_notification('ConferenceUpdated', self,
                                                   NotificationData(room_number=room_number,
                                                                    status='closed'))
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

        log.info('remove_session before remove room.length %r', room.length)
        log.info('remove_session for room.sessions %r', room.sessions)
        if session in room.sessions:
            log.info('remove_session room.remove_session ')
            room.remove_session(session)

        log.info('remove_session room.length %r', room.length)
        # 2 because the other participant is the music server
        # todo - check why we had to change this to 1 here
        if room.length <= 1:
            # we need to stop the remaining session
            log.info('check terminate all sessions room_data.status %r', room_data.status)
            if (room_data.status != 'on_hold') or (room.length == 0):
                log.info('terminate all sessions room %s', room_number)
                room.terminate_sessions()
                room_data.status = 'closed'
                # mark all the participants in the room as inactive and
                if room_data.hold_timer != None:
                    room_data.hold_timer.stop()
                    room_data.hold_timer = None
            NotificationCenter().post_notification('ConferenceUpdated', self,
                                                   NotificationData(room_number=room_number,
                                                                    status='closed'))

        if not room.stopping and room.empty:
            self.remove_room(room_number)
            room.stop()

    def add_outgoing_participant(self, display_name, sip_uri, session, is_calltaker=False, is_primary=False):
        self.add_participant(display_name, sip_uri, session, 'out', False, False, is_calltaker, is_primary)

    def add_incoming_participant(self, display_name, sip_uri, session, is_caller, is_calltaker):
        self.add_participant(display_name, sip_uri, session, 'in', False, is_caller, is_calltaker)

    def add_participant(self, display_name, sip_uri, session, direction, mute_audio, is_caller, is_calltaker=False, is_primary=False):
        room_number = session.room_number
        room_data = self.get_room_data(room_number)
        participants = room_data.participants

        # check if the participant is on hold
        if room_data.status == 'on_hold':
            if room_data.hold_timer != None:
                room_data.hold_timer.stop()
                room_data.hold_timer = None
            NotificationCenter().post_notification('ConferenceHoldUpdated', self,
                                                   NotificationData(room_number=room_number,
                                                                    calltaker=display_name,
                                                                    on_hold=False))
        if str(sip_uri) in participants:
            participant_data = participants[str(sip_uri)]
        else:
            participant_data = ParticipantData()

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
                                                                display_name=display_name))

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
        log.info('room_data is %r', room_data)
        log.info('room_data.participants is %r', room_data.participants)

        for participant_data in room_data.participants.itervalues():
            log.info('participant_data is %r', participant_data)
            if (participant_data.session == session) and (not participant_data.on_hold):
                participant_data.is_active = False
                participant_data.on_hold=False
                if participant_data.is_calltaker and participant_data.is_primary:
                    log.info('remove_participant found primary calltaker is %r', participant_data.display_name)
                    (has_new_primary, new_primary_uri) = self.set_new_primary(participants=room_data.participants, primary_calltaker_uri=str(participant_data.uri))
                    if has_new_primary:
                        participant_data.is_primary = False
                        NotificationCenter().post_notification('ConferenceParticipantNewPrimary', self,
                                                               NotificationData(room_number=room_number,
                                                                                old_primary_uri=str(participant_data.uri),
                                                                                new_primary_uri=str(new_primary_uri)))
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

    def put_calltaker_on_hold(self, room_number, calltaker_name):
        try:
            log.info('inside put_calltaker_on_hold for room %s, calltaker %s', room_number, calltaker_name)
            calltaker_participant = self._get_calltaker_participant(room_number, calltaker_name)
            if calltaker_participant is None:
                raise ValueError("invalid calltaker %r for room %r" % (calltaker_name, room_number))
            if calltaker_participant.on_hold:
                return
            calltaker_participant.on_hold = True
            room = self.get_room(room_number)
            room_data = self.get_room_data(room_number)
            #todo - finish this
            if room_data.status == 'active':
                # check if there is only one session in the call
                if len(room.sessions) == 1:
                    def hold_timer_cb(room_number):
                        hold_timer_cb.duration = hold_timer_cb.duration + 1
                        publish_update_call_timer(room_number, 'hold', hold_timer_cb.duration)

                    hold_timer_cb.duration = 0
                    hold_timer = task.LoopingCall(hold_timer_cb, room_number)
                    hold_timer.start(1)  # call every seconds
                    room_data.status = 'on_hold'
                    room_data.hold_timer = hold_timer
                    NotificationCenter().post_notification('ConferenceHoldUpdated', self,
                                                           NotificationData(room_number=room_number,
                                                                            calltaker=calltaker_name,
                                                                            on_hold=True))
            calltaker_participant.session.end()
            room.remove_session(calltaker_participant.session)

        except Exception as e:
            stacktrace = traceback.format_exc()
            log.error("error in put_calltaker_on_hold %s", str(e))
            log.error("%s", stacktrace)

    def mute_calltaker(self, room_number, name, muted):
        participant = self._get_calltaker_participant(room_number, name)
        if participant is None:
            raise ValueError("invalid calltaker %r for room %r" % (name, room_number))
        if participant.session is not None:
            if muted:
                participant.session.mute()
            else:
                participant.session.unmute()

        data = NotificationData(room_number=room_number, sip_uri=participant.uri, muted=muted)
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
        data = NotificationData(room_number=room_number, muted=muted)
        NotificationCenter().post_notification('ConferenceMuteAllUpdated', '', data)

    def mute_user(self, room_number, sip_uri, muted):
        pass

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
        except RoomNotFoundError:
            log.error("_NH_ConferenceParticipantDBUpdated room not found %r", room_number)

    def _NH_SIPSessionDidStart(self, notification):
        session = notification.sender
        log.info("PSAP _NH_SIPSessionDidStart %r, state %s", session, session.state)
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
        log.info('PSAP got _NH_SIPSessionDidEnd')
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
        log.info(u'PSAP Session from %s failed: %s' % (session.remote_identity.uri, notification.data.reason))
        self.remove_session(session)
        send_call_failed_notification(self, session=session, failure_code=notification.data.code, failure_reason=notification.data.reason)


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
    def __init__(self, target_uri, room_uri, caller_identity=None, is_calltaker=False, has_audio=True, has_chat=False):
        log.info("OutgoingCallInitializer for target %r, room %r, caller_identity %r, is_calltaker %r", target_uri, room_uri, caller_identity, is_calltaker)
        self.app = PSAPApplication()
        self.caller_identity = caller_identity
        self.room_uri = room_uri
        self.room_uri_str = '%s@%s' % (self.room_uri.user, self.room_uri.host)
        self.room_number = self.room_uri.user
        log.info("OutgoingCallInitializer room_number %r", self.room_number)
        self.target_uri = target_uri
        self.session = None
        self.cancel = False
        self.has_audio = has_audio
        self.has_chat = has_chat
        self.streams = []
        self.is_calltaker = is_calltaker

    def start(self):
        log.info("OutgoingCallInitializer start")
        if not self.target_uri.startswith(('sip:', 'sips:')):
            self.target_uri = 'sip:%s' % self.target_uri
        try:
            self.target_uri = SIPURI.parse(self.target_uri)
        except SIPCoreError:
            log.info('OutgoingCallInitializer start Room %s - failed to add %s' % (self.room_uri_str, self.target_uri))
            return
        log.info("OutgoingCallInitializer start")
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

    def cancel_call(self):
        self.cancel = True
        if self.session is not None:
            # todo add event sending here
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
            room = psap_application.get_room(self.room_number)
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
        if self.has_audio:
            self.streams.append(MediaStreamRegistry.AudioStream())
        if self.has_chat:
            self.streams.append(MediaStreamRegistry.ChatStream())

        self.session = Session(account)
        self.session.room_number = self.room_number
        self.session.is_primary = False
        self.session.is_calltaker = self.is_calltaker
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
        extra_headers.append(Header('X-Originator-From', str(self.caller_identity.uri)))
        extra_headers.append(SubjectHeader(u'Join conference request from %s' % self.caller_identity))
        route = notification.data.result[0]
        self.session.connect(from_header, to_header, route=route, streams=self.streams, is_focus=True, extra_headers=extra_headers)

    def _NH_SIPSessionNewOutgoing(self, notification):
        log.info('OutgoingCallInitializer got _NH_SIPSessionNewOutgoing')
        session = notification.sender
        send_call_update_notification(self, session, 'init')

    def _NH_DNSLookupDidFail(self, notification):
        notification_center = NotificationCenter()
        notification_center.remove_observer(self, sender=notification.sender)
        self.app.outgoing_session_lookup_failed(self.room_number, self.target_uri)

    def _NH_SIPSessionGotRingIndication(self, notification):
        session = notification.sender
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
        self.app.outgoing_session_did_start(self.target_uri, session)
        # self.app.add_outgoing_session(session)
        send_call_active_notification(self, session)
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
        self.app.outgoing_session_did_fail(session, self.target_uri, notification.data.code, notification.data.reason)
        send_call_failed_notification(self, session=session, failure_code=notification.data.code,
                                      failure_reason=notification.data.reason)

    def _NH_SIPSessionDidEnd(self, notification):
        # If any stream fails to start we won't get SIPSessionDidFail, we'll get here instead
        log.info('Room %s - ended %s' % (self.room_uri_str, self.target_uri))
        notification.center.remove_observer(self, sender=notification.sender)
        self.session = None
        self.streams = []
        session = notification.sender
        self.app.remove_session(session)
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
