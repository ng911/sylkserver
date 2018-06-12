from collections import namedtuple
import datetime
import traceback

from application.python import Null
from application.python.types import Singleton
from application.notification import IObserver, NotificationCenter
from sylk.applications import ApplicationLogger
from zope.interface import implements
from sylk.configuration import ServerConfig
from sylk.db.schema import Conference, ConferenceParticipant, ConferenceEvent
from sylk.wamp import publish_create_call, publish_update_call, publish_active_call, publish_update_primary
from sylk.db.calls import get_conference_json, get_conference_participants_json

import sylk.wamp

log = ApplicationLogger(__package__)

User = namedtuple('User', 'wamp_session_id username status')


class ConferenceData(object):
    """This class has only one instance"""
    __metaclass__ = Singleton
    implements(IObserver)

    def __init__(self):
        self.init_observers()

    def create_conference(self, room_number, direction='in', call_type='sos',
                          status='init', primary_queue_id=None, link_id=None, caller_ani='', caller_uri='', caller_name='',
                          has_audio=True, has_text=False, has_video=False, has_tty=False):
        try:
            log.info("inside create_conference")
            psap_id = ServerConfig.psap_id
            log.info("inside create_conference psap_id is %r", psap_id)
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

            '''
            participant = ConferenceParticipant()
            participant.room_number = room_number
            participant.name = caller_name
            participant.direction = direction
            participant.is_caller = True
            participant.is_calltaker = is_calltaker
            participant.sip_uri = caller_uri
            participant.save()
            '''

            call_data = get_conference_json(conference)
            participants_data = get_conference_participants_json(room_number)

            publish_create_call(room_number, call_data, participants_data)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in create_conference %r", e)
            log.error(stackTrace)

    def set_conference_active(self, room_number, calltakers):
        try:
            conference = Conference.objects.get(room_number=room_number)
            conference.status = 'active'
            utcnow = datetime.datetime.utcnow()
            conference.updated_at = utcnow
            conference.answer_time = utcnow
            conference.save()

            conference_event = ConferenceEvent()
            conference_event.event = 'active'
            conference_event.event_time = datetime.datetime.utcnow()
            conference_event.room_number = room_number
            conference_event.event_details = 'update call status to active'
            conference_event.save()

            call_data = get_conference_json(conference)
            participants_data = get_conference_participants_json(room_number)
            publish_update_call(room_number, call_data, participants_data)

            # todo- check, this one doesnt seem to be used by the calltaker. might remove it in future
            for calltaker in calltakers:
                publish_active_call(calltaker, room_number)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in update_conference_status %r", e)
            log.error(stackTrace)

    def update_conference_status(self, room_number, status):
        try:
            conference = Conference.objects.get(room_number=room_number)
            conference.status = status
            utcnow = datetime.datetime.utcnow()
            conference.updated_at = utcnow
            if (status == 'closed') or (status == 'abandoned'):
                conference.end_time = utcnow
            conference.save()

            if (status == 'closed'):
                conference_participants = ConferenceParticipant.objects(room_number=room_number)
                for participant in conference_participants:
                    participant.is_active = False
                    participant.on_hold = False
                    participant.save()

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

            call_data = get_conference_json(conference)
            participants_data = get_conference_participants_json(room_number)
            publish_update_call(room_number, call_data, participants_data)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in update_conference_status %r", e)
            log.error(stackTrace)


    def add_participant(self, room_number, display_name, sip_uri, direction, is_caller, is_calltaker, is_primary):
        try:
            log.info('add_participant %r for room %r, display_name %r', sip_uri, room_number, display_name)
            participant = ConferenceParticipant()
            participant.room_number = room_number
            participant.name = display_name
            participant.direction = direction
            participant.is_caller = is_caller
            participant.is_calltaker = is_calltaker
            participant.sip_uri = sip_uri
            participant.is_primary = is_primary
            participant.save()

            conference_event = ConferenceEvent()
            conference_event.event = 'join'
            conference_event.event_time = datetime.datetime.utcnow()
            conference_event.room_number = room_number
            conference_event.event_details = 'participant {} joined'.format(display_name)
            conference_event.save()

            conference = Conference.objects.get(room_number=room_number)
            call_data = get_conference_json(conference)
            participants_data = get_conference_participants_json(room_number)
            publish_update_call(room_number, call_data, participants_data)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in add_participant %r", e)
            log.error(stackTrace)

    def update_participant_active_status(self, room_number, display_name, sip_uri, is_active):
        try:
            participant = ConferenceParticipant.objects.get(room_number=room_number, sip_uri=sip_uri)
            participant.is_active = is_active
            participant.save()

            conference_event = ConferenceEvent()
            conference_event.event = 'leave'
            conference_event.event_time = datetime.datetime.utcnow()
            conference_event.room_number = room_number
            conference_event.event_details = 'participant {} left'.format(display_name)
            conference_event.save()

            '''
            json_data = get_json_from_db_obj(participant, include_fields=['is_active'])
            json_data['command'] = 'update_participant_status'
            publish_update_call(room_number, json_data)
            '''
            conference = Conference.objects.get(room_number=room_number)
            call_data = get_conference_json(conference)
            participants_data = get_conference_participants_json(room_number)
            publish_update_call(room_number, call_data, participants_data)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in update_participant_active_status %r", e)
            log.error(stackTrace)

    def update_primary_calltaker(self, room_number, old_primary_uri, new_primary_uri):
        try:
            participant = ConferenceParticipant.objects.get(room_number=room_number, sip_uri=old_primary_uri)
            participant.is_primary = False
            old_primary_user_name = participant.name
            participant.save()

            participant = ConferenceParticipant.objects.get(room_number=room_number, sip_uri=new_primary_uri)
            participant.is_primary = True
            new_primary_user_name = participant.name
            participant.save()

            '''
            todo add an event that primary is changed
            conference_event = ConferenceEvent()
            conference_event.event = 'leave'
            conference_event.event_time = datetime.datetime.utcnow()
            conference_event.room_number = room_number
            conference_event.event_details = 'participant {} left'.format(display_name)
            conference_event.save()
            '''

            '''
            json_data = get_json_from_db_obj(participant, include_fields=['is_active'])
            json_data['command'] = 'update_participant_status'
            publish_update_call(room_number, json_data)
            '''
            publish_update_primary(room_number, old_primary_user_name, new_primary_user_name)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in update_participant_active_status %r", e)
            log.error(stackTrace)

    def update_hold(self, room_number, calltaker, on_hold):
        try:
            participant = ConferenceParticipant.objects.get(room_number=room_number, name=calltaker, is_calltaker=True)
            participant.hold = on_hold
            participant.save()

            '''
            todo add an event that participant is on hold
            conference_event = ConferenceEvent()
            conference_event.event = 'leave'
            conference_event.event_time = datetime.datetime.utcnow()
            conference_event.room_number = room_number
            conference_event.event_details = 'participant {} left'.format(display_name)
            conference_event.save()
            '''
            conference = Conference.objects.get(room_number=room_number)
            if on_hold:
                conference.status = 'on_hold'
            else:
                conference.status = 'active'
            conference.save()
            call_data = get_conference_json(conference)
            participants_data = get_conference_participants_json(room_number)
            publish_update_call(room_number, call_data, participants_data)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in update_hold %r", e)
            log.error(stackTrace)

    def mute_participant(self, room_number, sip_uri, muted):
        try:
            participant = ConferenceParticipant.objects.get(room_number=room_number, sip_uri=sip_uri)
            participant.mute = muted
            participant.save()

            '''
            todo add an event that participant is on mute
            conference_event = ConferenceEvent()
            conference_event.event = 'leave'
            conference_event.event_time = datetime.datetime.utcnow()
            conference_event.room_number = room_number
            conference_event.event_details = 'participant {} left'.format(display_name)
            conference_event.save()
            '''
            conference = Conference.objects.get(room_number=room_number)
            call_data = get_conference_json(conference)
            participants_data = get_conference_participants_json(room_number)
            publish_update_call(room_number, call_data, participants_data)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in update_hold %r", e)
            log.error(stackTrace)

    def mute_all_participants(self, room_number, muted):
        try:
            for participant in ConferenceParticipant.objects(room_number=room_number, is_active=True):
                participant.muted = muted
                participant.save()

            '''
            todo add an event that participant is on mute
            conference_event = ConferenceEvent()
            conference_event.event = 'leave'
            conference_event.event_time = datetime.datetime.utcnow()
            conference_event.room_number = room_number
            conference_event.event_details = 'participant {} left'.format(display_name)
            conference_event.save()
            '''
            conference = Conference.objects.get(room_number=room_number)
            call_data = get_conference_json(conference)
            participants_data = get_conference_participants_json(room_number)
            publish_update_call(room_number, call_data, participants_data)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in update_hold %r", e)
            log.error(stackTrace)

    def init_observers(self):
        log.info("ConferenceData init_observers")
        notification_center = NotificationCenter()
        notification_center.add_observer(self, name='ConferenceCreated')
        notification_center.add_observer(self, name='ConferenceActive')
        notification_center.add_observer(self, name='ConferenceUpdated')
        notification_center.add_observer(self, name='ConferenceParticipantAdded')
        notification_center.add_observer(self, name='ConferenceParticipantRemoved')
        notification_center.add_observer(self, name='ConferenceParticipantNewPrimary')
        notification_center.add_observer(self, name='ConferenceHoldUpdated')
        notification_center.add_observer(self, name='ConferenceMuteUpdated')
        notification_center.add_observer(self, name='ConferenceMuteAllUpdated')

    def handle_notification(self, notification):
        log.info("ConferenceData got notification ")
        handler = getattr(self, '_NH_%s' % notification.name, Null)
        handler(notification)

    def _NH_ConferenceCreated(self, notification):
        log.info("incoming _NH_ConferenceCreated")
        try:
            self.create_conference(**notification.data.__dict__)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in _NH_ConferenceCreated %r", e)
            log.error(stackTrace)

    def _NH_ConferenceActive(self, notification):
        log.info("incoming _NH_ConferenceActive")
        try:
            self.set_conference_active(**notification.data.__dict__)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in _NH_ConferenceActive %r", e)
            log.error(stackTrace)

    def _NH_ConferenceUpdated(self, notification):
        log.info("incoming _NH_ConferenceUpdated")
        try:
            self.update_conference_status(notification.data.room_number, notification.data.status)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in _NH_ConferenceUpdated %r", e)
            log.error(stackTrace)

    def _NH_ConferenceParticipantAdded(self, notification):
        log.info("incoming _NH_ConferenceParticipantAdded")
        try:
            self.add_participant(**notification.data.__dict__)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in _NH_ConferenceParticipantAdded %r", e)
            log.error(stackTrace)

    def _NH_ConferenceParticipantRemoved(self, notification):
        log.info("incoming _NH_ConferenceParticipantRemoved")
        try:
            self.update_participant_active_status(notification.data.room_number, notification.data.display_name, notification.data.sip_uri, False)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in _NH_ConferenceParticipantRemoved %r", e)
            log.error(stackTrace)

    def _NH_ConferenceParticipantNewPrimary(self, notification):
        log.info("incoming _NH_ConferenceParticipantNewPrimary")
        try:
            self.update_primary_calltaker(notification.data.room_number, notification.data.old_primary_uri, notification.data.new_primary_uri)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in _NH_ConferenceParticipantNewPrimary %r", e)
            log.error(stackTrace)

    def _NH_ConferenceHoldUpdated(self, notification):
        log.info("incoming _NH_ConferenceHoldUpdated")
        try:
            self.update_hold(notification.data.room_number, notification.data.calltaker, notification.data.on_hold)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in _NH_ConferenceParticipantNewPrimary %r", e)
            log.error(stackTrace)

    def _NH_ConferenceMuteUpdated(self, notification):
        log.info("incoming _NH_ConferenceMuteUpdated")
        try:
            self.mute_participant(notification.data.room_number, notification.data.sip_uri, notification.data.muted)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in _NH_ConferenceMuteUpdated %r", e)
            log.error(stackTrace)

    def _NH_ConferenceMuteAllUpdated(self, notification):
        log.info("incoming _NH_ConferenceMuteAllUpdated")
        try:
            self.mute_all_participants(notification.data.room_number, notification.data.muted)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in _NH_ConferenceMuteAllUpdated %r", e)
            log.error(stackTrace)

