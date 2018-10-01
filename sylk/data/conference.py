from collections import namedtuple
import datetime
import traceback

from sipsimple.core import SIPURI
from application.python import Null
from application.python.types import Singleton
from application.notification import IObserver, NotificationCenter
from sylk.applications import ApplicationLogger
from zope.interface import implements
from sylk.configuration import ServerConfig
from sylk.db.schema import Conference, ConferenceParticipant, ConferenceEvent
from sylk.wamp import publish_create_call, publish_update_call, publish_active_call, publish_update_primary, publish_update_call_events
import sylk.db.calls as calls

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
                          called_number='', ali_format='', has_audio=True, has_text=False, has_video=False, has_tty=False):
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
            conference.ali_format = ali_format
            conference.start_time = cur_time
            conference.updated_at = cur_time
            conference.save()

            conference_event = ConferenceEvent()
            conference_event.event = 'init'
            conference_event.event_time = cur_time
            if direction == 'in':
                conference_event.event_details = 'Incoming call from {}'.format(caller_ani)
            else:
                conference_event.event_details = 'Outgoing call from {} to {} '.format(caller_ani, called_number)

            conference_event.room_number = room_number
            conference_event.save()

            '''
            conference_event = ConferenceEvent()
            conference_event.event = 'ringing'
            conference_event.event_time = datetime.datetime.utcnow()
            conference_event.event_details = 'call ringing '
            conference_event.room_number = room_number
            conference_event.save()
            '''
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

            call_data = calls.get_conference_json(conference)
            participants_data = calls.get_conference_participants_json(room_number)

            publish_create_call(room_number, call_data, participants_data)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in create_conference %r", e)
            log.error(stackTrace)

    def outgoing_call(self, room_number, display_name, is_calltaker):
        try:
            log.info("inside outgoing_call")
            cur_time = datetime.datetime.utcnow()
            conference_event = ConferenceEvent()
            conference_event.event = 'init'
            conference_event.event_time = cur_time
            if is_calltaker:
                conference_event.event_details = 'Calling calltaker {} '.format(display_name)
            else:
                conference_event.event_details = 'Calling {} '.format(display_name)

            conference_event.room_number = room_number
            conference_event.save()
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

            '''
            conference_event = ConferenceEvent()
            conference_event.event = 'active'
            conference_event.event_time = datetime.datetime.utcnow()
            conference_event.room_number = room_number
            conference_event.event_details = 'update call status to active'
            conference_event.save()
            '''

            call_data = calls.get_conference_json(conference)
            participants_data = calls.get_conference_participants_json(room_number)
            publish_update_call(room_number, call_data, participants_data)

            # todo- check, this one doesnt seem to be used by the calltaker. might remove it in future
            for calltaker in calltakers:
                publish_active_call(calltaker, room_number)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in update_conference_status %r", e)
            log.error(stackTrace)

    def on_conference_answered(self, room_number, display_name, is_calltaker, status):
        try:
            conference_event = ConferenceEvent()
            conference_event.event = 'active'
            conference_event.event_time = datetime.datetime.utcnow()
            conference_event.room_number = room_number
            if status != 'active':
                if is_calltaker:
                    conference_event.event_details = 'Calltaker {} answered the call'.format(display_name)
                else:
                    conference_event.event_details = '{} answered the call'.format(display_name)
            else:
                if is_calltaker:
                    conference_event.event_details = 'Calltaker {} joined the call'.format(display_name)
                else:
                    conference_event.event_details = '{} joined the call'.format(display_name)

            conference_event.save()
            publish_update_call_events(room_number)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in on_conference_answered %r", e)
            log.error(stackTrace)

    def on_conference_leave(self, room_number, display_name, is_calltaker, status):
        try:
            conference_event = ConferenceEvent()
            conference_event.event = 'leave'
            conference_event.event_time = datetime.datetime.utcnow()
            conference_event.room_number = room_number
            if is_calltaker:
                conference_event.event_details = 'Calltaker {} released the call'.format(display_name)
            else:
                conference_event.event_details = '{} hung up'.format(display_name)

            conference_event.save()
            publish_update_call_events(room_number)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in on_conference_leave %r", e)
            log.error(stackTrace)

    def on_conference_timedout(self, room_number):
        try:
            conference_event = ConferenceEvent()
            conference_event.event = 'timed_out'
            conference_event.event_time = datetime.datetime.utcnow()
            conference_event.room_number = room_number
            conference_event.event_details = 'Call timed out'

            conference_event.save()
            publish_update_call_events(room_number)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in on_conference_timedout %r", e)
            log.error(stackTrace)

    '''
    def on_conference_call_failed(self, room_number, display_name, is_calltaker, reason):
        try:
            conference_event = ConferenceEvent()
            conference_event.event = 'failed'
            conference_event.event_time = datetime.datetime.utcnow()
            conference_event.room_number = room_number
            if is_calltaker:
                conference_event.event_details = 'Call to Calltaker {} failed'.format(display_name)
            else:
                conference_event.event_details = 'Call to {} failed'.format(display_name)

            conference_event.save()
            publish_update_call_events(room_number)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in on_conference_timedout %r", e)
            log.error(stackTrace)
    '''

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
                for participant in ConferenceParticipant.objects(room_number=room_number):
                    participant.is_active = False
                    participant.hold = False
                    participant.save()

            '''
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
            '''
            '''
            if status == 'abandoned':
                conference_event = ConferenceEvent()
                conference_event.event = status
                conference_event.event_details = 'call timed out'
                conference_event.event_time = datetime.datetime.utcnow()
                conference_event.room_number = room_number
                conference_event.save()
            '''

            call_data = calls.get_conference_json(conference)
            participants_data = calls.get_conference_participants_json(room_number)
            publish_update_call(room_number, call_data, participants_data)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in update_conference_status %r", e)
            log.error(stackTrace)

    def add_participant_ringing(self, room_number, display_name):
        conference_event = ConferenceEvent()
        conference_event.event = 'ringing'
        conference_event.event_time = datetime.datetime.utcnow()
        conference_event.event_details = 'ringing {}'.format(display_name)
        conference_event.room_number = room_number
        conference_event.save()
        publish_update_call_events(room_number)

    def add_participant_timedout(self, room_number, display_name):
        conference_event = ConferenceEvent()
        conference_event.event = 'ringing'
        conference_event.event_time = datetime.datetime.utcnow()
        conference_event.event_details = 'timed out ringing to {} '.format(display_name)
        conference_event.room_number = room_number
        conference_event.save()
        publish_update_call_events(room_number)

    def add_participant_failed(self, room_number, display_name):
        conference_event = ConferenceEvent()
        conference_event.event = 'failed'
        conference_event.event_time = datetime.datetime.utcnow()
        conference_event.event_details = 'call to {} failed'.format(display_name)
        conference_event.room_number = room_number
        conference_event.save()
        publish_update_call_events(room_number)

    def add_participant(self, room_number, display_name, sip_uri, mute_audio, direction, is_caller, is_calltaker, is_primary):
        try:
            log.info('add_participant %r for room %r, display_name %r', sip_uri, room_number, display_name)

            participant = None
            if is_calltaker:
                # check if the participant already exists
                try:
                    participant = ConferenceParticipant.objects.get(room_number=room_number, is_calltaker=True, name=display_name)
                except:
                    pass
            else:
                try:
                    participant = ConferenceParticipant.objects.get(room_number=room_number, is_calltaker=False, sip_uri=str(sip_uri))
                except:
                    pass

            if participant is None:
                participant = ConferenceParticipant()
            participant.room_number = room_number
            participant.name = display_name
            participant.direction = direction
            participant.is_caller = is_caller
            participant.is_calltaker = is_calltaker
            participant.sip_uri = sip_uri
            participant.is_primary = is_primary
            participant.is_active = True
            participant.mute = mute_audio
            participant.save()

            '''
            conference_event = ConferenceEvent()
            conference_event.event = 'join'
            conference_event.event_time = datetime.datetime.utcnow()
            conference_event.room_number = room_number
            if is_calltaker:
                conference_event.event_details = 'Calltaker {} answered call'.format(display_name)
            else:
                conference_event.event_details = '{} answered call'.format(display_name)

            conference_event.save()
            '''

            conference = Conference.objects.get(room_number=room_number)
            call_data = calls.get_conference_json(conference)
            participants_data = calls.get_conference_participants_json(room_number)
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

            '''
            conference_event = ConferenceEvent()
            if is_active:
                conference_event.event = 'join'
                conference_event.event_details = 'participant {} is active'.format(display_name)
            else:
                conference_event.event = 'leave'
                conference_event.event_details = 'participant {} is inactive'.format(display_name)

            conference_event.event_time = datetime.datetime.utcnow()
            conference_event.room_number = room_number
            conference_event.save()
            '''

            '''
            json_data = get_json_from_db_obj(participant, include_fields=['is_active'])
            json_data['command'] = 'update_participant_status'
            publish_update_call(room_number, json_data)
            '''
            conference = Conference.objects.get(room_number=room_number)
            call_data = calls.get_conference_json(conference)
            participants_data = calls.get_conference_participants_json(room_number)
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

            conference_event = ConferenceEvent()
            conference_event.event = 'update_primary'
            conference_event.event_time = datetime.datetime.utcnow()
            conference_event.room_number = room_number
            old_sip_uri = SIPURI(old_primary_uri)
            new_sip_uri = SIPURI(new_primary_uri)
            conference_event.event_details = 'primary calltaker changed from {} to {}'.format(old_sip_uri.user, new_sip_uri.user)
            conference_event.save()

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

    # this should only be called if participant hold status is changed without call hold status being changed
    # todo - we prob need to remove this bad logic and combine with function below
    def update_participant_hold_status(self, room_number, calltaker, on_hold):
        log.info("inside update_participant_hold_status for room_number {}, calltaker {}, on_hold {}".format(room_number, calltaker, on_hold))
        participant = ConferenceParticipant.objects.get(room_number=room_number, name=calltaker, is_calltaker=True)
        participant.is_primary = False
        if on_hold:
            participant.is_active = False
        else:
            participant.is_active = True
        participant.hold = on_hold
        participant.save()

        conference_event = ConferenceEvent()
        conference_event.event_time = datetime.datetime.utcnow()
        conference_event.room_number = room_number
        if on_hold:
            conference_event.event = 'start_hold'
            conference_event.event_details = 'Call put on hold by {}'.format(calltaker)
        else:
            conference_event.event_details = 'Call taken off hold by {}'.format(calltaker)
        conference_event.save()
        conference = Conference.objects.get(room_number=room_number)
        call_data = calls.get_conference_json(conference)
        if call_data['status'] == 'on_hold':
            on_hold_by = []
            for participant in ConferenceParticipant.objects(room_number=room_number, name=calltaker, is_calltaker=True,
                                                             hold=True):
                on_hold_by.append(participant.name)
            if len(on_hold_by) > 0:
                call_data['on_hold_by'] = on_hold_by
        '''
        if on_hold:
            # get the calltakers that started on hold
            for participant in ConferenceParticipant.objects(room_number=room_number, name=calltaker, is_calltaker=True,
                                                             hold=True):
                on_hold_by.append(participant.name)
            call_data['on_hold_by'] = on_hold_by
        else:
            # make sure we remove hold done by calltaker
            for participant in ConferenceParticipant.objects(room_number=room_number, is_calltaker=True, hold=True):
                participant.hold = False
                participant.save()
        '''
        participants_data = calls.get_conference_participants_json(room_number)
        publish_update_call(room_number, call_data, participants_data)

    def update_call_hold(self, room_number, calltaker, on_hold):
        try:
            participant = ConferenceParticipant.objects.get(room_number=room_number, name=calltaker, is_calltaker=True)
            if on_hold:
                participant.is_active = False
                participant.is_primary = False
            else:
                participant.is_active = True
                participant.is_primary = True
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
            conference_event = ConferenceEvent()
            conference_event.event_time = datetime.datetime.utcnow()
            conference_event.room_number = room_number
            if on_hold:
                conference.status = 'on_hold'
                conference_event.event = 'start_hold'
                conference_event.event_details = 'Call put on hold by {}'.format(calltaker)
            else:
                conference_event.event = 'end_hold'
                conference_event.event_details = 'Call taken off hold by {}'.format(calltaker)
                conference.status = 'active'
            conference_event.save()
            conference.save()
            call_data = calls.get_conference_json(conference)
            if on_hold:
                # get the calltakers that started on hold
                on_hold_by = []
                for participant in ConferenceParticipant.objects(room_number=room_number, name=calltaker, is_calltaker=True, hold=True):
                    on_hold_by.append(participant.name)
                call_data['on_hold_by'] = on_hold_by
            #else:
            #    # make sure we remove hold done by calltaker
            #    for participant in ConferenceParticipant.objects(room_number=room_number, is_calltaker=True, hold=True):
            #        participant.hold = False
            #        participant.save()
            participants_data = calls.get_conference_participants_json(room_number)
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

            conference_event = ConferenceEvent()
            sip_uri_parsed = SIPURI.parse(str(sip_uri))
            username = sip_uri_parsed.user
            if muted:
                conference_event.event = 'mute'
                conference_event.event_details = 'participant {} muted'.format(username)
            else:
                conference_event.event = 'end_mute'
                conference_event.event_details = 'participant {} unmuted'.format(username)

            conference_event.event_time = datetime.datetime.utcnow()
            conference_event.room_number = room_number
            conference_event.save()

            conference = Conference.objects.get(room_number=room_number)
            call_data = calls.get_conference_json(conference)
            participants_data = calls.get_conference_participants_json(room_number)
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
            conference_event = ConferenceEvent()
            if muted:
                conference_event.event = 'mute'
                conference_event.event_details = 'all participants muted'
            else:
                conference_event.event = 'end_mute'
                conference_event.event_details = 'all participants unmuted'

            conference_event.event_time = datetime.datetime.utcnow()
            conference_event.room_number = room_number
            conference_event.save()

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
            call_data = calls.get_conference_json(conference)
            participants_data = calls.get_conference_participants_json(room_number)
            publish_update_call(room_number, call_data, participants_data)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in update_hold %r", e)
            log.error(stackTrace)

    def init_observers(self):
        log.info("ConferenceData init_observers")
        notification_center = NotificationCenter()
        notification_center.add_observer(self, name='ConferenceCreated')
        notification_center.add_observer(self, name='ConferenceOutgoingCall')
        notification_center.add_observer(self, name='ConferenceActive')
        notification_center.add_observer(self, name='ConferenceAnswered')
        notification_center.add_observer(self, name='ConferenceLeave')
        notification_center.add_observer(self, name='ConferenceUpdated')
        notification_center.add_observer(self, name='ConferenceParticipantAdded')
        notification_center.add_observer(self, name='ConferenceParticipantRemoved')
        notification_center.add_observer(self, name='ConferenceParticipantNewPrimary')
        notification_center.add_observer(self, name='ConferenceParticipantRinging')
        notification_center.add_observer(self, name='ConferenceParticipantFailed')
        notification_center.add_observer(self, name='ConferenceParticipantTimedout')
        notification_center.add_observer(self, name='ConferenceParticipantHoldUpdated')
        notification_center.add_observer(self, name='ConferenceHoldUpdated')
        notification_center.add_observer(self, name='ConferenceMuteUpdated')
        notification_center.add_observer(self, name='ConferenceMuteAllUpdated')
        notification_center.add_observer(self, name='ConferenceTimedOut')
        #notification_center.add_observer(self, name='ConferenceCallFailed')


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

    def _NH_ConferenceOutgoingCall(self, notification):
        log.info("incoming _NH_ConferenceOutgoingCall")
        try:
            self.outgoing_call(**notification.data.__dict__)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in _NH_ConferenceOutgoingCall %r", e)
            log.error(stackTrace)

    def _NH_ConferenceActive(self, notification):
        log.info("incoming _NH_ConferenceActive")
        try:
            self.set_conference_active(**notification.data.__dict__)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in _NH_ConferenceActive %r", e)
            log.error(stackTrace)

    def _NH_ConferenceAnswered(self, notification):
        log.info("incoming _NH_ConferenceAnswered")
        try:
            self.on_conference_answered(**notification.data.__dict__)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in _NH_ConferenceAnswered %r", e)
            log.error(stackTrace)

    def _NH_ConferenceLeave(self, notification):
        log.info("incoming _NH_ConferenceLeave")
        try:
            self.on_conference_leave(**notification.data.__dict__)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in _NH_ConferenceLeave %r", e)
            log.error(stackTrace)

    def _NH_ConferenceTimedOut(self, notification):
        log.info("incoming _NH_ConferenceTimedOut")
        try:
            self.on_conference_timedout(**notification.data.__dict__)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in _NH_ConferenceTimedOut %r", e)
            log.error(stackTrace)

    '''
    def _NH_ConferenceCallFailed(self, notification):
        log.info("incoming _NH_ConferenceCallFailed")
        try:
            self.on_conference_call_failed(**notification.data.__dict__)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in _NH_ConferenceCallFailed %r", e)
            log.error(stackTrace)
    '''

    def _NH_ConferenceUpdated(self, notification):
        log.info("incoming _NH_ConferenceUpdated")
        try:
            self.update_conference_status(notification.data.room_number, notification.data.status)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in _NH_ConferenceUpdated %r", e)
            log.error(stackTrace)

    def _NH_ConferenceParticipantRinging(self, notification):
        log.info("incoming _NH_ConferenceParticipantRinging")
        try:
            self.add_participant_ringing(notification.data.room_number, notification.data.display_name)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in _NH_ConferenceParticipantRinging %r", e)
            log.error(stackTrace)

    def _NH_ConferenceParticipantFailed(self, notification):
        log.info("incoming _NH_ConferenceParticipantFailed")
        try:
            self.add_participant_failed(notification.data.room_number, notification.data.display_name)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in ConferenceParticipantFailed %r", e)
            log.error(stackTrace)

    def _NH_ConferenceParticipantTimedout(self, notification):
        log.info("incoming _NH_ConferenceParticipantTimedout")
        try:
            self.add_participant_timedout(notification.data.room_number, notification.data.display_name)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in ConferenceParticipantTimedout %r", e)
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

    def _NH_ConferenceParticipantHoldUpdated(self, notification):
        log.info("incoming _NH_ConferenceParticipantHoldUpdated")
        try:
            self.update_participant_hold_status(notification.data.room_number, notification.data.calltaker, notification.data.on_hold)
        except Exception as e:
            stackTrace = traceback.format_exc()
            log.error("exception in _NH_ConferenceParticipantNewPrimary %r", e)
            log.error(stackTrace)

    def _NH_ConferenceHoldUpdated(self, notification):
        log.info("incoming _NH_ConferenceHoldUpdated")
        try:
            self.update_call_hold(notification.data.room_number, notification.data.calltaker, notification.data.on_hold)
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

