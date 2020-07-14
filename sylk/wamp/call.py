import traceback
try:
    from sylk.applications import ApplicationLogger
    log = ApplicationLogger(__package__)
except:
    import logging
    log = logging.getLogger('emergent-ng911')

from .core import wamp_publish


def publish_update_calls():
    try:
        log.info("publish com.emergent.calls")
        wamp_publish(u'com.emergent.calls')
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
        wamp_publish(u'com.emergent.call', json_data)
    except Exception as e:
        stackTrace = traceback.format_exc()
        log.error("exception in wamp %s", str(e))
        log.error("%s", stackTrace)


def publish_active_call(calltaker, room_number):
    try:
        json_data = {}
        json_data['command'] = 'active'
        json_data['room_number'] = room_number
        wamp_publish(u'com.emergent.call.%s' % calltaker, json_data)
    except Exception as e:
        stackTrace = traceback.format_exc()
        log.error("exception in wamp %s", str(e))
        log.error("%s", stackTrace)


def publish_clear_abandoned_call(rooms):
    try:
        json_data = {}
        json_data['command'] = 'clear_abandoned'
        json_data['rooms'] = rooms
        wamp_publish(u'com.emergent.call', json_data)
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
        wamp_publish(u'com.emergent.calltimer', json_data)
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
        wamp_publish(u'com.emergent.call', json_data)
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
        wamp_publish(u'com.emergent.call', json_data)
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
        wamp_publish(u'com.emergent.call', json_data)
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
        wamp_publish(u'com.emergent.call.outgoing.%s' % calltaker, json_data)
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
        wamp_publish(u'com.emergent.call', json_data)
    except Exception as e:
        stackTrace = traceback.format_exc()
        log.error("exception in wamp %s", str(e))
        log.error("%s", stackTrace)

