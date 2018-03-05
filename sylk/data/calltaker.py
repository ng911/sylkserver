import datetime

from application.python import Null
from application.python.types import Singleton
from application.notification import IObserver, NotificationCenter
from sylk.applications import ApplicationLogger
from zope.interface import implements
from sylk.db.schema import Call
#from sylk.utils import dump_object_member_vars, dump_object_member_funcs

log = ApplicationLogger(__package__)

'''
Store Calltaker status in memory
'''
class CalltakerData(object):
    """This class has only one instance"""
    __metaclass__ = Singleton
    implements(IObserver)

    def __init__(self):
        self.init_observers()
        self.active_calltakers = {}

    def init_observers(self):
        log.info("CallData init_observers")
        notification_center = NotificationCenter()
        notification_center.add_observer(self, name='CalltakerUpdate')

    def handle_notification(self, notification):
        log.info("CallData got notification ")
        log.info("CallData got notification %r" % notification.name)
        handler = getattr(self, '_NH_%s' % notification.name, Null)
        handler(notification)

    def _NH_CalltakerUpdate(self, notification):
        log.info("incoming _NH_CalltakerUpdate")
        user_id = notification.data.user_id
        status = notification.data.status
        self.update_status(user_id, status)

    def status(self, user_id):
        if user_id in self.active_calltakers:
            return self.active_calltakers[user_id]
        return None

    def update_status(self, user_id, status):
        self.active_calltakers[user_id] = status




