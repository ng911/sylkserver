import logging
import traceback
import functools

log = logging.getLogger('emergent-ng911')


async def wait_for_db_change(future_data, node, model, schema_name, arguments_data, for_connection=False):
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
            if for_connection:
                future = future_data[0]
                if not future.done():
                    future.set_result(node())
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

    topic = f"com.emergent911.node.{schema_name}"
    log.info(f"wait_for_changes topic {topic}, wamp_session {wamp_session}")
    try:
        await wamp_session.subscribe(on_changed, topic)
    except:
        log.error("exception in wamp_session.subscribe")

def subsribe_for_node(node):
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
            loop.create_task(wait_for_db_change(future_data, node, model, model._get_collection_name(), kwargs))
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


def subsribe_for_connection(node, model):
    log.info("inside subsribe_for_node")
    def decorator(func):
        log.info("inside decorator")
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            from asyncio import get_event_loop, Future
            log.info("inside wrapped")
            loop = get_event_loop()
            future_data = []
            loop.create_task(wait_for_db_change(future_data, node, model, model._get_collection_name(), kwargs, for_connection=True))
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



