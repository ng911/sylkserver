import logging
import traceback
import json
from six import u

from autobahn.asyncio.component import Component
from autobahn.asyncio.component import run
from autobahn.wamp.types import PublishOptions

log = logging.getLogger('emergent-ng911')

from ..config import WAMP_CROSSBAR_SERVER

log.info("wamp session start")

comp = Component(
     #transports=u"ws://127.0.0.1:8080/ws",
    #transports=WAMP_CROSSBAR_SERVER,
    transports=u("wss://staging-webservice.supportgenie.io/ws"),
    realm=u("realm1"),
    extra="tarun"
)
#comp.log = my_log

wamp_session=None
start_status_listener = False
# wamp session client information for each user wamp session
wamp_session_client_data = {}
# wamp sessions for each user
user_wamp_sessions = {}

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

def get_wamp_session():
    return wamp_session

async def wamp_publish(topic, json_data=None, exclude_me=True):
    try:
        if wamp_session is not None:
            #log.debug("my_wamp_publish %s, json %r",topic, json_data)
            if json_data is None:
                json_data = {}
            await wamp_session.publish(topic, json_data, options=PublishOptions(acknowledge=True,
                                                                         exclude_me=exclude_me))

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
async def joined(session, details):
    global wamp_session
    log.info("wamp joined")
    log.info("wamp session ready %r, id %r", session, session._session_id)
    wamp_session = session


@comp.on_leave
async def left(session, details):
    global wamp_session
    log.error("wamp session left, session")
    log.error("wamp session left, session is %r, old session is %r, details %r", session, wamp_session, details)
    wamp_session = None
    # todo - try to reconnect here
    start()


@comp.on_disconnect
async def on_disconnect(session):
    global wamp_session
    log.error("wamp session disconnected")
    wamp_session = None


def start():
    try:
        log.info("connecting wamp to %r", WAMP_CROSSBAR_SERVER)
        #reactor.callFromThread(comp.start)
        run([comp], start_loop=False)
    except Exception as e:
        log.error ("error in wamo start")
        log.error (str(e))

