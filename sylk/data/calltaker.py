import datetime
from collections import namedtuple

from application.python import Null
from application.python.types import Singleton
from application.notification import IObserver, NotificationCenter
from sylk.applications import ApplicationLogger
from zope.interface import implements
from sylk.db.schema import Call
#from sylk.utils import dump_object_member_vars, dump_object_member_funcs

log = ApplicationLogger(__package__)

User = namedtuple('User', 'wamp_session_id username status')

'''
Store Calltaker status in memory
'''
class CalltakerData(object):
    """This class has only one instance"""
    __metaclass__ = Singleton
    implements(IObserver)

    def __init__(self):
        self.init_observers()
        self._calltakers = {}
        self._wamp_sessions = {}

    def init_observers(self):
        log.info("CallData init_observers")
        notification_center = NotificationCenter()
        notification_center.add_observer(self, name='CalltakerStatus')
        notification_center.add_observer(self, name='CalltakerSessionLeave')

    def handle_notification(self, notification):
        log.info("CallData got notification ")
        log.info("CallData got notification %r" % notification.name)
        handler = getattr(self, '_NH_%s' % notification.name, Null)
        handler(notification)

    def _NH_CalltakerStatus(self, notification):
        log.info("incoming _NH_CalltakerStatus")
        user_id = notification.data.user_id
        wamp_session_id = notification.data.wamp_session_id
        if wamp_session_id not in self._wamp_sessions:
            self._wamp_sessions[wamp_session_id] = user_id
        status = notification.data.status
        username = notification.data.username
        self._calltakers[user_id] = User(wamp_session_id=wamp_session_id, status=status, username=username)

    def _NH_CalltakerSessionLeave(self, notification):
        log.info("incoming _NH_CalltakerSessionLeave")
        wamp_session_id = notification.data
        if wamp_session_id in self._wamp_sessions:
            user_id = self._wamp_sessions[wamp_session_id]
            if user_id in self._calltakers:
                user = self._calltakers[user_id]
                if user._wamp_session_id == wamp_session_id:
                    user.status = "offline"
                    user.wamp_session_id = None

    def status(self, user_id):
        if user_id in self._calltakers:
            return self._calltakers[user_id].status
        return "offline"

    @property
    def calltakers(self):
        calltakers = []
        for user_id, calltaker in self._calltakers.iteritems():
            calltakers.append({'user_id' : user_id, 'username' : calltaker.username, 'status' : calltaker.status })
        return calltakers


