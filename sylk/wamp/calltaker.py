import traceback
import time
try:
    from sylk.applications import ApplicationLogger
    log = ApplicationLogger(__package__)
except:
    import logging
    log = logging.getLogger('emergent-ng911')

from .core import wamp_publish

def publish_update_calltaker_status(user_id, username, status):
    try:
        json_data = {
            'username': username,
            'user_id': user_id,
            'status': status,
            'update_time' : time.time()
        }
        #log.info("publish_update_calltaker_status for json %r", json_data)
        wamp_publish(u'com.emergent.calltaker', json_data)
    except Exception as e:
        stackTrace = traceback.format_exc()
        log.error("exception in wamp %s", str(e))
        log.error("%s", stackTrace)


def publish_update_calltakers(json_data):
    try:
        wamp_publish(u'com.emergent.calltakers', json_data)
    except Exception as e:
        stackTrace = traceback.format_exc()
        log.error("exception in wamp %s", str(e))
        log.error("%s", stackTrace)
