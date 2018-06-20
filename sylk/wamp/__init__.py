from autobahn.twisted.component import Component
from sylk.applications import ApplicationLogger
from application.notification import IObserver, NotificationCenter, NotificationData
from sylk.utils import dump_object_member_vars, dump_object_member_funcs
log = ApplicationLogger(__package__)
from twisted.internet.defer import inlineCallbacks, returnValue
import sylk.data.calltaker as calltaker

log.info("wamp session start")

comp = Component(
     transports=u"ws://159.65.73.31:8080/ws",
     realm=u"realm1",
     extra="tarun"
 )


wamp_session=None


def publish_update_calltaker_status(user_id, username, status):
    if wamp_session is not None:
        json_data = {
            'username': username,
            'user_id': user_id,
            'status': status
        }
        log.info("publish_update_calltaker_status for json %r", json_data)
        wamp_session.publish(u'com.emergent.calltaker', json_data)
    else:
        log.error("publish_update_calltaker_status wamp session is None")


def publish_update_calltakers(json_data):
    if wamp_session is not None:
        wamp_session.publish(u'com.emergent.calltakers', json_data)


def publish_create_call(room_number, call_data, participants):
    if wamp_session is not None:
        json_data = {}
        json_data['command'] = 'created'
        json_data['room_number'] = room_number
        json_data['call_data'] = call_data
        json_data['participants'] = participants
        #log.info("publish com.emergent.call with json %r", json_data)
        wamp_session.publish(u'com.emergent.call', json_data)


def publish_active_call(calltaker, room_number):
    if wamp_session is not None:
        json_data = {}
        json_data['command'] = 'active'
        json_data['room_number'] = room_number
        wamp_session.publish(u'com.emergent.call.%s' % calltaker, json_data)

# type should be ringing or duration
def publish_update_call_timer(room_number, type, val):
    if wamp_session is not None:
        json_data = {}
        json_data['type'] = type
        json_data['val'] = val
        wamp_session.publish(u'com.emergent.calltimer.%s' % room_number, json_data)


def publish_update_call(room_number, call_data, participants=None):
    if wamp_session is not None:
        json_data = {}
        json_data['command'] = 'updated'
        json_data['room_number'] = room_number
        json_data['call_data'] = call_data
        if participants is not None:
            json_data['participants'] = participants

        #log.info("publish com.emergent.call with json %r", json_data)
        wamp_session.publish(u'com.emergent.call', json_data)

# status can be 'ringing', 'active', 'failed', 'timedout'
def publish_outgoing_call_status(room_number, calltaker, status):
    if wamp_session is not None:
        json_data = {}
        json_data['status'] = status
        json_data['room_number'] = room_number
        wamp_session.publish(u'com.emergent.call.outgoing.%s' % calltaker, json_data)


def publish_update_primary(room_number, old_primary_user_name, new_primary_user_name):
    log.info("publish_update_primary room_number %r, old_primary_user_name %r, new_primary_user_name %r", room_number, old_primary_user_name, new_primary_user_name)
    if wamp_session is not None:
        json_data = {}
        json_data['command'] = 'primary_updated'
        json_data['room_number'] = room_number
        json_data['old_primary'] = old_primary_user_name
        json_data['new_primary'] = new_primary_user_name

        #log.info("publish com.emergent.call with json %r", json_data)
        wamp_session.publish(u'com.emergent.call', json_data)


def publish_update_location_success(room_number, ali_result, location_display):
    json_data = {'success' : True, 'room_number': room_number, 'ali_data' : ali_result, 'location_display' : location_display}
    if wamp_session is not None:
        log.info("publish location update for room %s", room_number)
        wamp_session.publish(u'com.emergent.location', json_data)


def publish_update_location_failed(room_number):
    json_data = {'success' : False}
    if wamp_session is not None:
        wamp_session.publish(u'com.emergent.location.%s' % room_number, json_data)

def publish_update_calls():
    if wamp_session is not None:
        log.info("publish com.emergent.calls")
        wamp_session.publish(u'com.emergent.calls')

@comp.on_join
@inlineCallbacks
def joined(session, details):
    global wamp_session
    log.info("wamp session ready %r, id %r", session, session._session_id)
    # make sure calltaker is initialized
    calltaker.CalltakerData()
    wamp_session = session

    def on_calltaker_status(data):
        log.info("event on_calltaker_status received")
        log.info("event on_calltaker_status received: %r", data)
        log.info("event on_calltaker_status received: %r", data['command'])
        if data['command'] == 'status':
            log.info("process status command")
            notification_center = NotificationCenter()
            notification_data = NotificationData(username=data['username'], \
                                                  status=data['status'], wamp_session_id=data['wamp_session_id'], user_id=data['user_id'])
            notification_center.post_notification('CalltakerStatus', session, notification_data)
            out = {
                'command' : 'status_updated'
            }
            session.publish(u'com.emergent.calltakers', out)
            log.info("sent status_updated")

    def on_session_leave(data):
        log.info("on_session_leave event received")
        log.info("on_session_leave event received: %r", data)
        notification_center = NotificationCenter()
        notification_center.post_notification('CalltakerSessionLeave', session, NotificationData(wamp_session_id=data))
        out = {
            'command': 'status_updated'
        }
        session.publish(u'com.emergent.calltakers', out)

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
    log.info("session left")
    wamp_session = None
    # todo - try to reconnect here


def start():
     comp.start()
