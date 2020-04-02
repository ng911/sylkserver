
from application.notification import IObserver, NotificationCenter, NotificationData

# status can be 'init', 'accept', 'reject', 'closed'
def send_call_status_update_notification(sender, user_id, username, status, wamp_session_id):
    notification_center = NotificationCenter()
    notification_data = NotificationData(username=username,
                                         status=status, wamp_session_id=wamp_session_id,
                                         user_id=user_id)
    notification_center.post_notification('CalltakerStatus', sender, notification_data)





