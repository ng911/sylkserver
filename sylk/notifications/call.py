from application.notification import IObserver, NotificationCenter, NotificationData

# status can be 'init', 'accept', 'reject', 'closed'
def send_call_update_notification(sender, session, status):
    notification_center = NotificationCenter()
    notification_center.post_notification('DataCallUpdate', sender, NotificationData(session=session, status=status))

