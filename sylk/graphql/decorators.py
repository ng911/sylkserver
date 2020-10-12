import logging
import traceback
import functools

log = logging.getLogger('emergent-ng911')

from enum import Enum
class WaitForDbChangeType(Enum):
    NEW_NODE = 0
    NODE = 1
    CONNECTION = 2
    CONNECTION_TEST = 3


async def wait_for_db_change(future_data, node, model, schema_name, arguments_data, \
                             change_type=WaitForDbChangeType.NODE, test_change_lambda=None):
    from ..wamp_asyncio import get_wamp_session
    wamp_session = get_wamp_session()

    def on_changed(*args, **kwargs):
        log.info("on_changed args %r, kwargs %r", args, kwargs)
        #print(f"onWebRTCMessage {args}, {kwargs}")
        try:
            if (len(args) != 0) and (isinstance(args, list) or isinstance(args, tuple)):
                json_data = args[0]
            elif len(kwargs) != 0:
                json_data = kwargs
            else:
                log.error("event on_changed received with empty data")
                return
            log.info("got json_data")
            #model = root._meta.model
            if change_type == WaitForDbChangeType.CONNECTION:
                do_notify = False
                if test_change_lambda != None:
                    document_json = json_data['document_json']
                    modelObj = model.from_json(document_json)
                    if test_change_lambda(modelObj):
                        do_notify = True
                else:
                    do_notify = True
                if do_notify:
                    future = future_data[0]
                    if not future.done():
                        future.set_result(node())
            elif change_type == WaitForDbChangeType.CONNECTION_TEST:
                future = future_data[0]
                if not future.done():
                    future.set_result(model.objects())
            elif change_type == WaitForDbChangeType.NEW_NODE:
                document_json = json_data['document_json']
                modelObj = model.from_json(document_json)
                log.info(f"on_changed got document_json {document_json}")
                log.info("arguments_data is %r", arguments_data)
                future = future_data[0]
                if not future.done():
                    future.set_result(modelObj)
                log.info("furure result set")
            else:
                document_json = json_data['document_json']
                modelObj = model.from_json(document_json)
                log.info(f"on_changed got document_json {document_json}")
                #log.info(f"on_changed model {model}")
                #yield UserNode(model.from_json(document_json))
                log.info("arguments_data is %r", arguments_data)
                send_notification = True
                if arguments_data != None:
                    for arg, val in arguments_data.items():
                        if getattr(modelObj, arg) != val:
                            send_notification = False
                if send_notification:
                    future = future_data[0]
                    if not future.done():
                        future.set_result(modelObj)
                log.info("furure result set")
        except Exception as e:
            stacktrace = traceback.format_exc()
            log.error(stacktrace)
            log.error(str(e))

    if change_type == WaitForDbChangeType.NEW_NODE:
        topic = f"com.emergent911.node.new.{schema_name}"
    else:
        topic = f"com.emergent911.node.{schema_name}"

    log.info(f"wait_for_changes topic {topic}, wamp_session {wamp_session}")
    try:
        await wamp_session.subscribe(on_changed, topic)
    except:
        log.error("exception in wamp_session.subscribe")


from asyncio import get_event_loop, Future

def resolve_subscription_relay_helper(node, model, arguments_data, change_type, test_change_lambda=None):
    log.info("inside wrapped model is %r", model)
    log.info("inside resolve_user kwargs is %r", arguments_data)
    loop = get_event_loop()
    future_data = []
    loop.create_task(
        wait_for_db_change(future_data, node, model, model._get_collection_name(), arguments_data, change_type=change_type, test_change_lambda=test_change_lambda))
    while True:
        future_data.clear()
        future = Future()
        future_data.append(future)
        await future
        log.info("await future done")
        result = future.result()
        log.info("got result %r", result)
        yield result

def resolve_subscription_for_relay_new_node(node, args):
    log.info("inside wrapped")
    model = node._meta.model
    resolve_subscription_relay_helper(node, model, args, WaitForDbChangeType.NEW_NODE)

def resolve_subscription_for_relay_node(node, **args):
    log.info("inside wrapped")
    model = node._meta.model
    resolve_subscription_relay_helper(node, model, args, WaitForDbChangeType.NODE)

def resolve_subscription_for_relay_connection(node, model, args, test_change_lambda=None):
    resolve_subscription_relay_helper(node, model, args, WaitForDbChangeType.CONNECTION, test_change_lambda)

def subsribe_for_node(node, is_new=False):
    log.info("inside subsribe_for_node")
    def decorator(func):
        log.info("inside decorator")
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            from asyncio import get_event_loop, Future
            log.info("inside wrapped")
            model = node._meta.model
            log.info("inside wrapped model is %r", model)
            log.info("inside resolve_user kwargs is %r", kwargs)
            loop = get_event_loop()
            future_data = []
            change_type = WaitForDbChangeType.NODE

            if is_new:
                change_type = WaitForDbChangeType.NEW_NODE
            loop.create_task(wait_for_db_change(future_data, node, model, model._get_collection_name(), kwargs, change_type=change_type))
            while True:
                future_data.clear()
                future = Future()
                future_data.append(future)
                await future
                log.info("await future done")
                result = future.result()
                log.info("got result %r", result)
                yield result

        return wrapped
    return decorator


def subsribe_for_connection(node, model, experimantal=False):
    log.info("inside subsribe_for_node")
    def decorator(func):
        log.info("inside decorator")
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            from asyncio import get_event_loop, Future
            log.info("inside wrapped")
            loop = get_event_loop()
            future_data = []
            if experimantal:
                change_type = WaitForDbChangeType.CONNECTION_TEST
            else:
                change_type = WaitForDbChangeType.CONNECTION
            loop.create_task(wait_for_db_change(future_data, node, model, model._get_collection_name(), kwargs,
                                                change_type=change_type))
            while True:
                future_data.clear()
                future = Future()
                future_data.append(future)
                await future
                log.info("await future done")
                result = future.result()
                log.info("got result %r", result)
                yield result

        return wrapped
    return decorator



