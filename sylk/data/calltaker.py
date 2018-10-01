import time
from collections import namedtuple

from application.python import Null
from application.python.types import Singleton
from application.notification import IObserver, NotificationCenter, NotificationData
from sylk.applications import ApplicationLogger
from zope.interface import implements
#from sylk.utils import dump_object_member_vars, dump_object_member_funcs
import sylk.wamp

log = ApplicationLogger(__package__)

User = namedtuple('User', 'wamp_session_id username status janus_busy')

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
        handler = getattr(self, '_NH_%s' % notification.name, Null)
        handler(notification)

    def _NH_CalltakerStatus(self, notification):
        log.info("incoming _NH_CalltakerStatus")
        user_id = notification.data.user_id
        wamp_session_id = str(notification.data.wamp_session_id)
        if wamp_session_id not in self._wamp_sessions:
            self._wamp_sessions[wamp_session_id] = user_id
        status = notification.data.status
        username = notification.data.username
        janus_busy = notification.data.janus_busy
        self._calltakers[user_id] = User(wamp_session_id=wamp_session_id, status=status, username=username, janus_busy=janus_busy)
        self.notify_status_updated(user_id, username, status, janus_busy)

    def notify_status_updated(self, user_id, username, status, janus_busy):
        notification_data = NotificationData(username=username, \
                                             status=status, \
                                             janus_busy=janus_busy, \
                                             user_id=user_id)
        sylk.wamp.publish_update_calltaker_status(user_id, username, status)
        NotificationCenter().post_notification('CalltakerStatusUpdate', self, notification_data)

    def _NH_CalltakerSessionLeave(self, notification):
        log.info("incoming _NH_CalltakerSessionLeave")
        wamp_session_id = str(notification.data.wamp_session_id)
        if wamp_session_id in self._wamp_sessions:
            user_id = self._wamp_sessions[wamp_session_id]
            del self._wamp_sessions[wamp_session_id]
            if user_id in self._calltakers:
                user = self._calltakers[user_id]
                if user.wamp_session_id == wamp_session_id:
                    del self._calltakers[user_id]
                    self.notify_status_updated(user_id, user.username, 'offline', False)

    def status(self, user_id):
        if user_id in self._calltakers:
            return self._calltakers[user_id].status
        return "offline"

    def update_status(self, user_id, status):
        if user_id in self._calltakers:
            user = self._calltakers[user_id]
            self._calltakers[user_id] = User(wamp_session_id=user.wamp_session_id, status=status, username=user.username, janus_busy=user.janus_busy)
            self.notify_status_updated(user_id, user.username, status, user.janus_busy)
            '''
            notification_data = NotificationData(username=user.username, \
                                                 status=status, \
                                                 user_id=user_id)
            NotificationCenter().post_notification('CalltakerStatusUpdate', self, notification_data)
            sylk.wamp.publish_update_calltaker_status(user_id, user.username, status)
            '''
        else:
            log.error('user_id %r not found in _calltakers %r', user_id, self._calltakers)

    def is_janus_busy(self, user_id):
        if user_id in self._calltakers:
            return self._calltakers[user_id].janus_busy
        return False

    def update_janus_status(self, user_id, is_busy):
        if user_id in self._calltakers:
            user = self._calltakers[user_id]
            self._calltakers[user_id] = User(wamp_session_id=user.wamp_session_id, status=user.status, username=user.username, janus_busy=is_busy)
            self.notify_status_updated(user_id, user.username, user.status, is_busy)
            '''
            notification_data = NotificationData(username=user.username, \
                                                 status=status, \
                                                 user_id=user_id)
            NotificationCenter().post_notification('CalltakerStatusUpdate', self, notification_data)
            sylk.wamp.publish_update_calltaker_status(user_id, user.username, status)
            '''
        else:
            log.error('user_id %r not found in _calltakers %r', user_id, self._calltakers)

    @property
    def calltakers(self):
        calltakers = []
        for user_id, calltaker in self._calltakers.iteritems():
            calltakers.append({'user_id' : user_id, 'username' : calltaker.username, 'status' : calltaker.status,
                               'update_time' : time.time(), 'janus_busy' : calltaker.janus_busy })
        return calltakers

    @property
    def available_calltakers(self):
        return {user_id: user for user_id, user in self._calltakers.iteritems() if user.status == 'available'}

