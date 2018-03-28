from application.notification import IObserver, NotificationCenter, NotificationData

# status can be 'created', 'add_participant', 'mute_caller', 'unmute_caller', 'mute_participant', 'unmute_participant, 'start'
def send_conference_create_notification(sender, room, session, status):
    notification_center = NotificationCenter()
    notification_center.post_notification('DataConferenceCreate', sender, NotificationData(session=session, status=status))

def send_conference_queued_notification(sender, room):
    notification_center = NotificationCenter()
    notification_center.post_notification('DataConferenceQueued', sender, NotificationData(room=room))

def send_conference_start_notification(sender, room):
    notification_center = NotificationCenter()
    notification_center.post_notification('DataConferenceStart', sender, NotificationData(room=room))

def send_conference_abandoned_notification(sender, room):
    notification_center = NotificationCenter()
    notification_center.post_notification('DataConferenceAbandoned', sender, NotificationData(room=room))

def send_conference_closed_notification(sender, room):
    notification_center = NotificationCenter()
    notification_center.post_notification('DataConferenceClosed', sender, NotificationData(room=room))

def send_conference_add_participant_notification(sender, room, participant_session):
    notification_center = NotificationCenter()
    notification_center.post_notification('DataConferenceAddParticipant', sender, NotificationData(session=participant_session, room=room))

def send_conference_leave_participant_notification(sender, room, participant_session):
    notification_center = NotificationCenter()
    notification_center.post_notification('DataConferenceLeaveParticipant', sender, NotificationData(session=participant_session, room=room))

