import logging, traceback
from mongoengine import *
from mongoengine import signals

log = logging.getLogger("emergent-ng911")


def post_save(sender, document, **kwargs):
    from ...config import USE_ASYNCIO
    if USE_ASYNCIO:
        import asyncio
        log.info("importing publish_relay_node_update from asyncio")
        from ...wamp_asyncio import publish_relay_node_update, publish_relay_node_add
    else:
        log.info("importing publish_relay_node_update from twisted")
        from ...wamp import publish_relay_node_update, publish_relay_node_add
    try:
        log.info("inside graphql_node_notifications post_save ")
        #node_name = "%sNode" % document.__class__.__name__
        schema_name = document._get_collection_name()
        log.info("inside graphql_node_notifications post_save %r, id %r", schema_name, document.id)
        log.info("inside graphql_node_notifications kwargs %r, document.psap_id %r", kwargs, document.psap_id)
        log.info("inside graphql_node_notifications psap_id %r, id %r, node_name %s", document.psap_id, document.id,
                 schema_name)
        if 'created' in kwargs and kwargs['created']:
            log.info("call publish_relay_node_add")
            if USE_ASYNCIO:
                loop = asyncio.get_running_loop()
                asyncio.ensure_future(publish_relay_node_add(document.to_json(), document.psap_id, document.id, schema_name),
                                      loop=loop)
            else:
                publish_relay_node_add(document.to_json(), document.psap_id, document.id, schema_name)
            log.info("call publish_relay_node_add done")
        else:
            log.info("call publish_relay_node_update")
            if USE_ASYNCIO:
                loop = asyncio.get_running_loop()
                asyncio.ensure_future(publish_relay_node_update(document.to_json(), document.psap_id, document.id, schema_name),
                                      loop=loop)
            else:
                publish_relay_node_update(document.to_json(), document.psap_id, document.id, schema_name)
            log.info("call publish_relay_node_update done")
    except Exception as e:
        stacktrace = traceback.format_exc()
        log.error(stacktrace)
        log.error(e)


def graphql_node_notifications(cls):
    '''
    decorator for generating graphql notifications
    :param key:
    :return:
    '''
    log.info("inside graphql_node_notifications add signals %r", cls.__name__)
    signals.post_save.connect(post_save, sender=cls)
    return cls

