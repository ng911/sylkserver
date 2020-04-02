from application.notification import NotificationCenter, NotificationData

# status can be 'init', 'accept', 'reject', 'closed'
def send_call_update_notification(sender, session, status):
    NotificationCenter().post_notification('DataCallUpdate', sender, NotificationData(session=session, status=status))

def send_call_active_notification(sender, session):
    NotificationCenter().post_notification('DataCallActive', sender, NotificationData(session=session, room_number=session.room_number))

def send_call_failed_notification(sender, session, failure_code, failure_reason):
    NotificationCenter().post_notification('DataCallFailed', sender, NotificationData(session=session, failure_code=failure_code, failure_reason=failure_reason))
