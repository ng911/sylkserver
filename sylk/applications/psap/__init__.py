
from application.notification import IObserver, NotificationCenter, NotificationData
from application.python import Null
from sipsimple.account.bonjour import BonjourPresenceState
from twisted.internet import reactor
from zope.interface import implements

from sylk.applications import SylkApplication, ApplicationLogger
from sipsimple.streams import MediaStreamRegistry
from sipsimple.core import Engine, SIPCoreError, SIPURI, ToHeader
from sipsimple.lookup import DNSLookup
from sipsimple.configuration.settings import SIPSimpleSettings
from sipsimple.session import IllegalStateError, Session
from sylk.accounts import DefaultAccount, UserAccount
from sipsimple.account import Account
from sylk.applications import ApplicationRegistry
from uuid import uuid4

from sylk.db.authenticate import authenticate_call
from sylk.db.queue import get_queue_details, get_queue_members
from acd import get_calltakers
from sylk.data.call import CallData
from sylk.configuration import ServerConfig
#from sylk.utils import dump_object_member_vars, dump_object_member_funcs, dump_var

log = ApplicationLogger(__package__)


def format_identity(identity):
    if identity.display_name:
        return u'%s <sip:%s@%s>' % (identity.display_name, identity.uri.user, identity.uri.host)
    else:
        return u'sip:%s@%s' % (identity.uri.user, identity.uri.host)

def get_conference_application():
    application_registry = ApplicationRegistry()
    return application_registry.get('conference')

class PSAPApplication(SylkApplication):
    implements(IObserver)

    def __init__(self):
        log.info(u'PSAPApplication init')
        CallData()

    def start(self):
        log.info(u'PSAPApplication start')

    def stop(self):
        log.info(u'PSAPApplication stop')

    def incoming_session(self, session):
        log.info(u'New incoming session %s from %s' % (session.call_id, format_identity(session.remote_identity)))
        #dump_object_member_vars(log, session)
        #dump_object_member_funcs(log, session)

        audio_streams = [stream for stream in session.proposed_streams if stream.type=='audio']
        chat_streams = [stream for stream in session.proposed_streams if stream.type=='chat']
        if not audio_streams and not chat_streams:
            log.info(u'Session %s rejected: invalid media, only RTP audio and MSRP chat are supported' % session.call_id)
            session.reject(488)
            return
        if audio_streams:
            session.send_ring_indication()

        remote_identity = session.remote_identity
        local_identity = session.local_identity
        peer_address = session.peer_address

        conference_application = get_conference_application()
        rooms = conference_application.get_rooms()

        # first verify the session
        (authenticated, call_type, data) = authenticate_call(peer_address.ip, peer_address.port, local_identity.uri.user, remote_identity.uri, rooms)

        notification_center = NotificationCenter()
        notification_center.post_notification('DataCallUpdate', self, NotificationData(session=session, status='init'))

        if not authenticated:
            log.info("call not authenticated, reject it")
            session.reject(403)
            notification_center.post_notification('DataCallUpdate', self,
                                                  NotificationData(session=session, status='reject'))
            return


        if call_type == 'sos':
            inoming_link = data
            queue_details = get_queue_details(inoming_link.queue_id)
            queue_members = get_queue_members(inoming_link.queue_id)
            calltakers = get_calltakers(queue_details, queue_members)
            server = ServerConfig.asterisk_server
            sip_uris = ["sip:%s@%s" % (calltaker.username, server) for calltaker in calltakers.itervalues()]
            log.info("sip_uris is %r", sip_uris)
            room_number = uuid4().hex

            for sip_uri in sip_uris:
                log.info("create outgoing call to sip_uri %r", sip_uri)
                # create an outbound session here for calls to calltakers
                self.outgoingCallInitializer = OutgoingCallInitializer(incoming_session=session,
                                                                       target=sip_uri,
                                                                       audio=True,
                                                                       room_number=room_number,
                                                                       user=remote_identity.uri.user)
                self.outgoingCallInitializer.start()
        elif call_type == 'sos_room':
            pass
        elif call_type == 'outgoing':
            pass
        elif call_type == 'admin':
            pass

    def incoming_subscription(self, request, data):
        request.reject(405)

    def incoming_referral(self, request, data):
        request.reject(405)

    def incoming_message(self, request, data):
        request.reject(405)


class OutgoingCallInitializer(object):
    implements(IObserver)

    def __init__(self, incoming_session, target, audio=False, chat=False, room_number=None, user=None):
        log.info("OutgoingCallInitializer user is %r", user)
        self.account = DefaultAccount()
        self.account.user = user

        self.target = target
        self.streams = []
        self.incoming_session = incoming_session
        if audio:
            self.streams.append(MediaStreamRegistry.AudioStream())
        if chat:
            self.streams.append(MediaStreamRegistry.ChatStream())
        self.wave_ringtone = None
        self.room_number = room_number

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

    def handle_notification(self, notification):
        handler = getattr(self, '_NH_%s' % notification.name, Null)
        handler(notification)

    def _NH_DNSLookupDidSucceed(self, notification):
        notification_center = NotificationCenter()
        notification_center.remove_observer(self, sender=notification.sender)
        session = Session(self.account)
        notification_center.add_observer(self, sender=session)
        session.connect(ToHeader(self.target), routes=notification.data.result, streams=self.streams)
        #application = SIPSessionApplication()
        #application.outgoing_session = session
        #self.app.outgoing_session = session

    def _NH_DNSLookupDidFail(self, notification):
        log.info('Call to %s failed: DNS lookup error: %s' % (self.target, notification.data.error))
        notification_center = NotificationCenter()
        notification_center.remove_observer(self, sender=notification.sender)

    def _NH_SIPSessionNewOutgoing(self, notification):
        session = notification.sender
        local_identity = str(session.local_identity.uri)
        if session.local_identity.display_name:
            local_identity = '"%s" <%s>' % (session.local_identity.display_name, local_identity)
        remote_identity = str(session.remote_identity.uri)
        if session.remote_identity.display_name:
            remote_identity = '"%s" <%s>' % (session.remote_identity.display_name, remote_identity)
        log.info("Initiating SIP session from '%s' to '%s' via %s..." % (local_identity, remote_identity, session.route))

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

    def _NH_SIPSessionDidStart(self, notification):
        notification_center = NotificationCenter()
        #ui = UI()
        session = notification.sender
        notification_center.remove_observer(self, sender=session)
        remote_identity = str(session.remote_identity.uri)
        log.info("Session sarted %s, %s" % (remote_identity, session.route))

        log.info('startConference for room %s' % (self.room_number))
        session.room_number = self.room_number
        self.incoming_session.room_number = self.room_number

        conference_application = get_conference_application()

        conference_application.incoming_session(self.incoming_session)

        log.info(u'_NH_SIPSessionDidStart for session.room_number %s' % session.room_number)
        conference_application.add_outgoing_session(session)

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

