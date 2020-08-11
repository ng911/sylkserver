import traceback
import time
try:
    from sylk.applications import ApplicationLogger
    log = ApplicationLogger(__package__)
except:
    import logging
    log = logging.getLogger('emergent-ng911')

from .core import wamp_publish

def publish_msrp_message(psap_id, json_data):
    try:
        wamp_publish(u'com.emergent.call.msrp.%s' % psap_id, json_data)
    except Exception as e:
        stackTrace = traceback.format_exc()
        log.error("exception in publish_msrp_message %s", str(e))
        log.error("%s", stackTrace)

