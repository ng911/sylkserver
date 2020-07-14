import traceback
import json
import time

from autobahn.twisted.component import Component
from autobahn.wamp.types import PublishOptions
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet import reactor

try:
    from sylk.applications import ApplicationLogger
    log = ApplicationLogger(__package__)
except:
    import logging
    log = logging.getLogger('emergent-ng911')

from ..config import WAMP_CROSSBAR_SERVER

log.info("wamp session start")

comp = Component(
     #transports=u"ws://127.0.0.1:8080/ws",
    transports=WAMP_CROSSBAR_SERVER,
    realm=u"realm1",
    extra="tarun"
)
#comp.log = my_log

wamp_session=None
start_status_listener = False
# wamp session client information for each user wamp session
wamp_session_client_data = {}
# wamp sessions for each user
user_wamp_sessions = {}

def on_wamp_success(result):
    #log.debug("my_wamp_publish deferred on_success %r, %s", result, result)
    pass


def on_wamp_error(failure):
    log.error("my_wamp_publish deferred on_error")
    log.error("my_wamp_publish deferred on_error %r", failure)


'''
cur_wamp_request = {
    'topic' : '',
    'data' : None
}

pending_requests = []

def append_to_pending_request(topic, data):
    # create a unique id for this request
    key = uuid.uuid4()
    pending_requests[key] = {
        'topic' : topic,
        'data' : data
    }

def process_pending_requests():
    pending_requests_copy = pending_requests.copy()
    for key, request in pending_requests_copy.iter_items:
        @inlineCallbacks


@inlineCallbacks
def send_one_request(request):
    if request.data is None:
        json_data = {}
    else:
        json_data = request.data
    yield wamp_session.publish(request.topic, json_data, options=PublishOptions(acknowledge=True))
'''


def wamp_publish(topic, json_data=None):
    reactor.callFromThread(_wamp_publish, topic, json_data)


def _wamp_publish(topic, json_data=None):
    try:
        if wamp_session is not None:
            #log.debug("my_wamp_publish %s, json %r",topic, json_data)
            json_size = 0
            if json_data is not None:
                json_obj = json.dumps(json_data)
                json_size = len(json_obj)
                deferred = wamp_session.publish(topic, json_data, options=PublishOptions(acknowledge=True))
            else:
                deferred = wamp_session.publish(topic, {}, options=PublishOptions(acknowledge=True))

            deferred.addCallbacks(on_wamp_success, on_wamp_error)
            #deferred.addCallback(on_success)
            #deferred.addErrback(on_error)
        else:
            log.error("my_wamp_publish for %r, json %r, wamp session is None", topic, json_data)

    except Exception as e:
        stackTrace = traceback.format_exc()
        log.error("exception in wamp %s, topic %s, json %r", str(e), topic, json_data)
        log.error("%s", stackTrace)
    except:
        log.error("exception in wamp topic %s, json %r", topic, json_data)





@comp.on_join
@inlineCallbacks
def joined(session, details):
    global wamp_session
    log.info("wamp session ready %r, id %r", session, session._session_id)
    # make sure calltaker is initialized
    #calltaker_data.CalltakerData()
    wamp_session = session

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
        from application.notification import IObserver, NotificationCenter, NotificationData
        global  wamp_session_client_data, user_wamp_sessions
        if data['command'] == 'status':
            wamp_session_id = str(data['wamp_session_id'])
            user_id = str(data['user_id'])
            wamp_session_client_data[wamp_session_id] = {
                "user_id" : user_id
            }
            if user_id in user_wamp_sessions:
                user_id_wamp_sessions_data = user_wamp_sessions[user_id]
                if wamp_session_id not in user_id_wamp_sessions_data:
                    user_id_wamp_sessions_data.append(wamp_session_id)
                    user_wamp_sessions[user_id] = user_id_wamp_sessions_data
            else:
                user_wamp_sessions[user_id] = [wamp_session_id]
            status = str(data['status'])
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
            log.info("user_wamp_sessions %r", user_wamp_sessions)
            log.info("wamp_session_client_data %r", wamp_session_client_data)

    def on_session_leave(data):
        log.info("on_session_leave event received")
        log.info("on_session_leave event received: %r", data)
        # todo - fix , update database here
        global  wamp_session_client_data, user_wamp_sessions
        from application.notification import IObserver, NotificationCenter, NotificationData
        wamp_session_id = str(data)
        log.info("on_session_leave event received: wamp_session_client_data %r", wamp_session_client_data)
        if wamp_session_id in wamp_session_client_data:
            log.info("found wamp_session_id in wamp_session_client_data")
            client_data = wamp_session_client_data[wamp_session_id]
            user_id = client_data["user_id"]
            log.info("found user_id %r", user_id)
            del wamp_session_client_data[wamp_session_id]
            if user_id in user_wamp_sessions:
                log.info("found user_id %r in user_wamp_sessions", user_id)
                user_id_wamp_sessions_data = user_wamp_sessions[user_id]
                if wamp_session_id in user_id_wamp_sessions_data:
                    log.info("found wamp_session_id in user_id_wamp_sessions_data")
                    user_id_wamp_sessions_data.remove(wamp_session_id)
                log.info("len(user_wamp_sessions) %r", len(user_wamp_sessions))
                if len(user_id_wamp_sessions_data) == 0:
                    del user_wamp_sessions[user_id]
                else:
                    user_wamp_sessions[user_id] = user_id_wamp_sessions_data
            update_is_available(user_id)
            notification_center = NotificationCenter()
            notification_center.post_notification('CalltakerSessionLeave', wamp_session, NotificationData(wamp_session_id=data))
            out = {
                'command': 'status_updated'
            }
            session.publish(u'com.emergent.calltakers', out)

    if start_status_listener:
        try:
            # clear sessions and update is_available in database
            global wamp_session_client_data, user_wamp_sessions
            wamp_session_client_data = {}
            user_wamp_sessions = {}
            from ..db.calltaker import reset_calltakers_status
            from ..configuration import ServerConfig
            reset_calltakers_status(ServerConfig.psap_id)

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

    '''
    dump_object_member_vars(log, session)
    dump_object_member_funcs(log, session)
    log.info("wamp session id %r" % session._session_id)
    log.info("wamp confog %r" % session.config)
    dump_object_member_vars(log, session.config)
    dump_object_member_funcs(log, session.config)
    log.info("wamp config extra %r" % session.config.extra)
    '''

@comp.on_leave
@inlineCallbacks
def left(session, details):
    global wamp_session
    log.error("wamp session left, session")
    log.error("wamp session left, session is %r, old session is %r, details %r", session, wamp_session, details)
    wamp_session = None
    # todo - try to reconnect here
    start()

@comp.on_disconnect
@inlineCallbacks
def on_disconnect(session):
    global wamp_session
    log.error("wamp session disconnected")
    wamp_session = None


def start(status_listner_enabled=False):
    try:
        global start_status_listener
        start_status_listener = status_listner_enabled
        log.info("connecting wamp to %r", WAMP_CROSSBAR_SERVER)
        #reactor.callFromThread(comp.start)
        comp.start()
    except Exception as e:
        log.error ("error in wamo start")
        log.error (str(e))

