import traceback
import json
import time

from autobahn.twisted.component import Component
from autobahn.wamp.types import PublishOptions
#from application.notification import IObserver, NotificationCenter, NotificationData
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


def my_wamp_publish(topic, json_data=None):
    reactor.callFromThread(wamp_publish, topic, json_data)


def wamp_publish(topic, json_data=None):
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


def publish_update_calltaker_status(user_id, username, status):
    try:
        json_data = {
            'username': username,
            'user_id': user_id,
            'status': status,
            'update_time' : time.time()
        }
        #log.info("publish_update_calltaker_status for json %r", json_data)
        my_wamp_publish(u'com.emergent.calltaker', json_data)
    except Exception as e:
        stackTrace = traceback.format_exc()
        log.error("exception in wamp %s", str(e))
        log.error("%s", stackTrace)


def publish_update_calltakers(json_data):
    try:
        my_wamp_publish(u'com.emergent.calltakers', json_data)
    except Exception as e:
        stackTrace = traceback.format_exc()
        log.error("exception in wamp %s", str(e))
        log.error("%s", stackTrace)



def publish_create_call(room_number, call_data, participants):
    try:
        json_data = {}
        json_data['command'] = 'created'
        json_data['room_number'] = room_number
        json_data['call_data'] = call_data
        json_data['participants'] = participants
        #log.info("publish com.emergent.call with json %r", json_data)
        my_wamp_publish(u'com.emergent.call', json_data)
    except Exception as e:
        stackTrace = traceback.format_exc()
        log.error("exception in wamp %s", str(e))
        log.error("%s", stackTrace)



def publish_active_call(calltaker, room_number):
    try:
        json_data = {}
        json_data['command'] = 'active'
        json_data['room_number'] = room_number
        my_wamp_publish(u'com.emergent.call.%s' % calltaker, json_data)
    except Exception as e:
        stackTrace = traceback.format_exc()
        log.error("exception in wamp %s", str(e))
        log.error("%s", stackTrace)



def publish_clear_abandoned_call(rooms):
    try:
        json_data = {}
        json_data['command'] = 'clear_abandoned'
        json_data['rooms'] = rooms
        my_wamp_publish(u'com.emergent.call', json_data)
    except Exception as e:
        stackTrace = traceback.format_exc()
        log.error("exception in wamp %s", str(e))
        log.error("%s", stackTrace)


# type should be ringing or duration
def publish_update_call_timer(room_number, type, val):
    try:
        json_data = {}
        json_data['type'] = type
        json_data['val'] = val
        json_data['room_number'] = room_number
        # todo - un remove this timer stuff after load test
        my_wamp_publish(u'com.emergent.calltimer', json_data)
    except Exception as e:
        stackTrace = traceback.format_exc()
        log.error("exception in wamp %s", str(e))
        log.error("%s", stackTrace)


def publish_update_call(room_number, call_data, participants=None):
    try:
        json_data = {}
        json_data['command'] = 'updated'
        json_data['room_number'] = room_number
        json_data['call_data'] = call_data
        if participants is not None:
            json_data['participants'] = participants

        log.info("publish com.emergent.call with call_data %r", call_data)
        my_wamp_publish(u'com.emergent.call', json_data)
    except Exception as e:
        stackTrace = traceback.format_exc()
        log.error("exception in wamp %s", str(e))
        log.error("%s", stackTrace)


def publish_update_call_ringing(room_number, ringing_calltakers):
    try:
        log.info("inside publish_update_call_ringing for room %s, calltakers %r", room_number, ringing_calltakers)
        json_data = {}
        json_data['command'] = 'ringing_updated'
        json_data['room_number'] = room_number
        json_data['ringing_calltakers'] = ringing_calltakers
        log.info("publish com.emergent.call with json_data %r", json_data)
        my_wamp_publish(u'com.emergent.call', json_data)
    except Exception as e:
        stackTrace = traceback.format_exc()
        log.error("exception in wamp %s", str(e))
        log.error("%s", stackTrace)


def publish_update_call_events(room_number):
    try:
        log.info("inside publish_update_call_events for room %s", room_number)
        json_data = {}
        json_data['command'] = 'events_updated'
        json_data['room_number'] = room_number
        log.info("publish com.emergent.call with json_data %r", json_data)
        my_wamp_publish(u'com.emergent.call', json_data)
    except Exception as e:
        stackTrace = traceback.format_exc()
        log.error("exception in wamp %s", str(e))
        log.error("%s", stackTrace)


# status can be 'ringing', 'active', 'failed', 'timedout'
def publish_outgoing_call_status(room_number, calltaker, status):
    try:
        json_data = {}
        json_data['status'] = status
        json_data['room_number'] = room_number
        my_wamp_publish(u'com.emergent.call.outgoing.%s' % calltaker, json_data)
    except Exception as e:
        stackTrace = traceback.format_exc()
        log.error("exception in wamp %s", str(e))
        log.error("%s", stackTrace)


def publish_update_primary(room_number, old_primary_user_name, new_primary_user_name):
    try:
        log.info("publish_update_primary room_number %r, old_primary_user_name %r, new_primary_user_name %r", room_number, old_primary_user_name, new_primary_user_name)
        json_data = {}
        json_data['command'] = 'primary_updated'
        json_data['room_number'] = room_number
        json_data['old_primary'] = old_primary_user_name
        json_data['new_primary'] = new_primary_user_name

        #log.info("publish com.emergent.call with json %r", json_data)
        my_wamp_publish(u'com.emergent.call', json_data)
    except Exception as e:
        stackTrace = traceback.format_exc()
        log.error("exception in wamp %s", str(e))
        log.error("%s", stackTrace)


def publish_update_location_success(room_number, ali_result, location_display):
    try:
        json_data = {'success' : True, 'room_number': room_number, 'ali_data' : ali_result, 'location_display' : location_display}
        log.info("publish location update for room %s", room_number)
        my_wamp_publish(u'com.emergent.location', json_data)
    except Exception as e:
        stackTrace = traceback.format_exc()
        log.error("exception in wamp %s", str(e))
        log.error("%s", stackTrace)


def publish_update_location_failed(room_number):
    try:
        json_data = {'success' : False}
        my_wamp_publish(u'com.emergent.location.%s' % room_number, json_data)
    except Exception as e:
        stackTrace = traceback.format_exc()
        log.error("exception in wamp %s", str(e))
        log.error("%s", stackTrace)


def publish_update_calls():
    try:
        log.info("publish com.emergent.calls")
        my_wamp_publish(u'com.emergent.calls')
    except Exception as e:
        stackTrace = traceback.format_exc()
        log.error("exception in wamp %s", str(e))
        log.error("%s", stackTrace)

def publish_tty_enabled(room_number):
    try:
        json_data = {}
        json_data['room_number'] = room_number
        my_wamp_publish(u'com.emergent.call.tty.enabled', json_data)
    except Exception as e:
        stackTrace = traceback.format_exc()
        log.error("exception in publish_tty_enabled %s", str(e))
        log.error("%s", stackTrace)

def publish_tty_updated(room_number):
    try:
        json_data = {}
        json_data['room_number'] = room_number
        my_wamp_publish(u'com.emergent.call.tty.updated', json_data)
    except Exception as e:
        stackTrace = traceback.format_exc()
        log.error("exception in publish_tty_updated %s", str(e))
        log.error("%s", stackTrace)

def publish_msrp_message(json_data):
    try:
        my_wamp_publish(u'com.emergent.call.msrp', json_data)
    except Exception as e:
        stackTrace = traceback.format_exc()
        log.error("exception in publish_msrp_message %s", str(e))
        log.error("%s", stackTrace)

@comp.on_join
@inlineCallbacks
def joined(session, details):
    global wamp_session
    log.info("wamp session ready %r, id %r", session, session._session_id)
    # make sure calltaker is initialized
    #calltaker_data.CalltakerData()
    wamp_session = session

    def update_is_available(user_id):
        from ..db.schema import User
        is_available = False
        if user_id in user_wamp_sessions:
            is_available = True
        userObj = User.objects.get(user_id=user_id)
        userObj.is_available = is_available
        userObj.save()

    def on_calltaker_status(data):
        log.info("event on_calltaker_status received")
        log.info("event on_calltaker_status received: %r", data)
        log.info("event on_calltaker_status received: %r", data['command'])
        # todo - fix , update database here
        global  wamp_session_client_data, user_wamp_sessions
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
        update_is_available(user_id)
        '''
        if data['command'] == 'status':
            log.info("process status command")
            notification_center = NotificationCenter()
            notification_data = NotificationData(username=data['username'], \
                                                  status=data['status'], wamp_session_id=data['wamp_session_id'], user_id=data['user_id'], janus_busy=data['janus_busy'])
            notification_center.post_notification('CalltakerStatus', session, notification_data)
            out = {
                'command' : 'status_updated'
            }
            session.publish(u'com.emergent.calltakers', out)
            log.info("sent status_updated")
        '''

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
        '''
        notification_center = NotificationCenter()
        notification_center.post_notification('CalltakerSessionLeave', session, NotificationData(wamp_session_id=data))
        '''
        '''
        out = {
            'command': 'status_updated'
        }
        session.publish(u'com.emergent.calltakers', out)
        '''

    try:
        yield session.subscribe(on_session_leave, u'wamp.session.on_leave')
        log.info("subscribed to wamp.session.on_leave")

        res = yield session.subscribe(on_calltaker_status, u'com.emergent.calltakers')
        log.info("subscribed to topic %r, id %r", res, res.id)
        data = {
            'command' : 'send_status_update'
        }

        yield session.publish(u'com.emergent.calltakers', data)
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


def start():
    try:
        log.info("connecting wamp to %r", WAMP_CROSSBAR_SERVER)
        reactor.callFromThread(comp.start)
        #comp.start()
    except Exception as e:
        log.error ("error in wamo start")
        log.error (str(e))

