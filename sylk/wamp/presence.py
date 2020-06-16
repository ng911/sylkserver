import traceback
import json
import time

from autobahn.twisted.component import Component
from autobahn.wamp.types import PublishOptions
from application.notification import IObserver, NotificationCenter, NotificationData
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet import reactor

try:
    from sylk.applications import ApplicationLogger
    log = ApplicationLogger(__package__)
except:
    import logging
    log = logging.getLogger('emergent-ng911')

# wamp session client information for each user wamp session
wamp_session_client_data = {}
# wamp sessions for each user
user_wamp_sessions = {}

@inlineCallbacks
def start_presence_listeners(wamp_session):
    def update_is_available(user_id, status="available"):
        from ..db.schema import User
        is_available = False
        if user_id in user_wamp_sessions:
            is_available = True
        userObj = User.objects.get(user_id=user_id)
        userObj.is_available = is_available
        if is_available:
            userObj.status = status
        else:
            userObj.status = "offline"
        userObj.save()

    def on_calltaker_status(data):
        log.info("event on_calltaker_status received")
        log.info("event on_calltaker_status received: %r", data)
        log.info("event on_calltaker_status received: %r", data['command'])
        # todo - fix , update database here
        global  wamp_session_client_data, user_wamp_sessions
        if data['command'] == 'status':
            wamp_session_id = data['wamp_session_id']
            user_id = data['user_id']
            wamp_session_client_data[wamp_session_id] = {
                "user_id" : user_id
            }
            if user_id in user_wamp_sessions:
                user_id_wamp_sessions_data = user_wamp_sessions[user_id]
                if wamp_session_id not in user_id_wamp_sessions_data:
                    user_id_wamp_sessions_data.append(wamp_session_id)
            else:
                user_wamp_sessions[user_id] = [wamp_session_id]
            status = data['status']
            update_is_available(user_id, status)

            log.info("process status command")
            notification_center = NotificationCenter()
            notification_data = NotificationData(username=data['username'], \
                                                  status=data['status'], wamp_session_id=data['wamp_session_id'], user_id=data['user_id'], janus_busy=data['janus_busy'])
            notification_center.post_notification('CalltakerStatus', wamp_session, notification_data)
            out = {
                'command' : 'status_updated'
            }
            wamp_session.publish(u'com.emergent.calltakers', out)
            log.info("sent status_updated")

    def on_session_leave(data):
        log.info("on_session_leave event received")
        log.info("on_session_leave event received: %r", data)
        # todo - fix , update database here
        global  wamp_session_client_data, user_wamp_sessions
        wamp_session_id = data
        if wamp_session_id in wamp_session_client_data:
            client_data = wamp_session_client_data[wamp_session_id]
            user_id = client_data["user_id"]
            del wamp_session_client_data[wamp_session_id]
            if user_id in user_wamp_sessions:
                user_id_wamp_sessions_data = user_wamp_sessions[user_id]
                if wamp_session_id in user_id_wamp_sessions_data:
                    user_wamp_sessions.remove(wamp_session_id)
                if len(user_wamp_sessions) == 0:
                    del user_wamp_sessions[user_id]
            update_is_available(user_id)
            notification_center = NotificationCenter()
            notification_center.post_notification('CalltakerSessionLeave', wamp_session, NotificationData(wamp_session_id=data))
        '''
        out = {
            'command': 'status_updated'
        }
        session.publish(u'com.emergent.calltakers', out)
        '''

    try:
        yield wamp_session.subscribe(on_session_leave, u'wamp.session.on_leave')
        log.info("subscribed to wamp.session.on_leave")

        res = yield wamp_session.subscribe(on_calltaker_status, u'com.emergent.calltakers')
        log.info("subscribed to topic %r, id %r", res, res.id)
        data = {
            'command' : 'send_status_update'
        }

        yield wamp_session.publish(u'com.emergent.calltakers', data)
        '''
        out = {
            'command': 'status_updated'
        }
        yield session.publish(u'com.emergent.calltakers', out)
        '''

    except Exception as e:
        log.info("exception in subscribe to topic: %r" % e)
