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

log.info("wamp session start for %r", WAMP_CROSSBAR_SERVER)

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
    pass
    #log.info("my_wamp_publish deferred on_success %r, %s", result, result)


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


def wamp_publish(topic, json_data=None, exclude_me=True):
    #log.info("inside wamp_publish twisted %s, json %r", topic, json_data)
    reactor.callFromThread(_wamp_publish, topic, json_data, exclude_me)


def _wamp_publish(topic, json_data=None, exclude_me=True):
    try:
        if wamp_session is not None:
            log.info("my_wamp_publish %s, json %r",topic, json_data)
            if json_data is None:
                json_data = {}
            deferred = wamp_session.publish(topic, json_data, options=PublishOptions(acknowledge=True,
                                                                                     exclude_me=exclude_me))
            deferred.addCallbacks(on_wamp_success, on_wamp_error)
            #deferred.addCallback(on_success)
            #deferred.addErrback(on_error)
        else:
            log.error("_wamp_publish for %r, json %r, wamp session is None", topic, json_data)

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
    log.info("wamp session ready for %r, session %r, id %r", WAMP_CROSSBAR_SERVER, session, session._session_id)
    # make sure calltaker is initialized
    #calltaker_data.CalltakerData()
    wamp_session = session

    if start_status_listener:
        from .presence import start_presence
        start_presence(session)

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

