import traceback
import time
try:
    from sylk.applications import ApplicationLogger
    log = ApplicationLogger(__package__)
except:
    import logging
    log = logging.getLogger('emergent-ng911')

from .core import wamp_publish

def publish_update_location_success(room_number, ali_result, location_display):
    try:
        json_data = {'success' : True, 'room_number': room_number, 'ali_data' : ali_result, 'location_display' : location_display}
        log.info("publish location update for room %s", room_number)
        wamp_publish(u'com.emergent.location', json_data)
    except Exception as e:
        stackTrace = traceback.format_exc()
        log.error("exception in wamp %s", str(e))
        log.error("%s", stackTrace)


def publish_update_location_failed(room_number):
    try:
        json_data = {'success' : False}
        wamp_publish(u'com.emergent.location.%s' % room_number, json_data)
    except Exception as e:
        stackTrace = traceback.format_exc()
        log.error("exception in wamp %s", str(e))
        log.error("%s", stackTrace)
