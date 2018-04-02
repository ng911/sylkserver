from collections import namedtuple
import datetime

from application.python import Null
from application.python.types import Singleton
from application.notification import IObserver, NotificationCenter
from sylk.applications import ApplicationLogger
from zope.interface import implements
from sylk.configuration import ServerConfig
from sylk.db.schema import Conference, ConferenceParticipant, ConferenceEvent
from sylk.wamp import publish_create_call, publish_update_call
from sylk.utils import get_json_from_db_obj
import sylk.wamp

log = ApplicationLogger(__package__)

User = namedtuple('User', 'wamp_session_id username status')


class ConferenceData(object):
    """This class has only one instance"""
    __metaclass__ = Singleton
    implements(IObserver)

    def __init__(self):
        self.init_observers()

    def create_conference(self, room_number, direction='incoming', call_type='sos',
                          status='init', primary_queue_id=None, link_id=None, caller_ani='', caller_uri='', caller_name='',
                          has_audio=True, has_text=False, has_video=False, has_tty=False):
        server = ServerConfig.asterisk_server
        psap_id = server.psap_id
        cur_time = datetime.datetime.utcnow()
        conference = Conference()
        conference.psap_id = psap_id
        conference.room_number = room_number
        conference.has_text = has_text
        conference.has_audio = has_audio
        conference.has_video = has_video
        conference.has_tty = has_tty
        conference.direction = direction
        conference.call_type = call_type
        conference.status = status
        conference.primary_queue_id = primary_queue_id
        conference.link_id = link_id
        conference.caller_ani = caller_ani
        conference.caller_uri = caller_uri
        conference.caller_name = caller_name
        conference.start_time = cur_time
        conference.updated_at = cur_time
        conference.save()

        conference_event = ConferenceEvent()
        conference_event.event = 'init'
        conference_event.event_time = cur_time
        conference_event.event_details = 'Incoming call from {}'.format(caller_ani)
        conference_event.room_number = room_number
        conference_event.save()

        conference_event = ConferenceEvent()
        conference_event.event = 'ringing'
        conference_event.event_time = datetime.datetime.utcnow()
        conference_event.event_details = 'send call ringing '.format()
        conference_event.room_number = room_number
        conference_event.save()

        json_data = get_json_from_db_obj(conference)
        publish_create_call(json_data)

    def update_conference_status(self, room_number, status):
        conference = Conference.objects.get(room_number=room_number)
        conference.status = status
        utcnow = datetime.datetime.utcnow()
        conference.updated_at = utcnow
        if status == 'active':
            conference.answer_time = utcnow
        elif (status == 'closed') or (status == 'abandoned'):
            conference.end_time = utcnow
        conference.save()

        conference_event = ConferenceEvent()
        conference_event.event = status
        conference_event.event_time = datetime.datetime.utcnow()
        conference_event.room_number = room_number
        if (status == 'closed'):
            conference_event.event_details = 'call ended'
        elif (status == 'abandoned'):
            conference_event.event_details = 'call timed out'
        else:
            conference_event.event_details = 'update call status to  {}'.format(status)
        conference_event.save()

        json_data = get_json_from_db_obj(conference, include_fields=['status'])
        json_data['command'] = 'update_status'
        publish_update_call(room_number, json_data)


    def add_participant(self, room_number, display_name, sip_uri, direction, is_caller):
        participant = ConferenceParticipant()
        participant.room_number = room_number
        participant.name = display_name
        participant.direction = direction
        participant.is_caller = is_caller
        participant.sip_uri = sip_uri
        participant.save()

        conference_event = ConferenceEvent()
        conference_event.event = 'join'
        conference_event.event_time = datetime.datetime.utcnow()
        conference_event.room_number = room_number
        conference_event.event_details = 'participant {} joined'.format(display_name)
        conference_event.save()

        json_data = get_json_from_db_obj(participant)
        json_data['command'] = 'add_participant'
        publish_update_call(room_number, json_data)

    def update_participant_active_status(self, room_number, display_name, sip_uri, is_active):
        participant = ConferenceParticipant.objects.get(room_number=room_number, sip_uri=sip_uri)
        participant.is_active = is_active
        participant.save()

        conference_event = ConferenceEvent()
        conference_event.event = 'leave'
        conference_event.event_time = datetime.datetime.utcnow()
        conference_event.room_number = room_number
        conference_event.event_details = 'participant {} left'.format(display_name)
        conference_event.save()

        json_data = get_json_from_db_obj(participant, include_fields=['is_active'])
        json_data['command'] = 'update_participant_status'
        publish_update_call(room_number, json_data)

    def init_observers(self):
        log.info("ConferenceData init_observers")
        notification_center = NotificationCenter()
        notification_center.add_observer(self, name='ConferenceCreated')
        notification_center.add_observer(self, name='ConferenceUpdated')
        notification_center.add_observer(self, name='ConferenceParticipantAdded')
        notification_center.add_observer(self, name='ConferenceParticipantRemoved')

    def handle_notification(self, notification):
        log.info("ConferenceData got notification ")
        handler = getattr(self, '_NH_%s' % notification.name, Null)
        handler(notification)

    def _NH_ConferenceCreated(self, notification):
        log.info("incoming _NH_ConferenceCreated")
        self.create_conference(**notification.data.__dict__)

    def _NH_ConferenceUpdated(self, notification):
        log.info("incoming _NH_ConferenceUpdated")
        self.update_conference_status(notification.data.room_number, notification.data.status)

    def _NH_ConferenceParticipantAdded(self, notification):
        log.info("incoming _NH_ConferenceUpdated")
        self.add_participant(**notification.data.__dict__)

    def _NH_ConferenceParticipantRemoved(self, notification):
        log.info("incoming _NH_ConferenceUpdated")
        self.update_participant_active_status(notification.data.room_number, notification.data.display_name, notification.data.sip_uri, False)
