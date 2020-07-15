import logging
import traceback

from .core import wamp_publish

log = logging.getLogger('emergent-ng911')

def base64(s):
    from base64 import b64encode as _base64, b64decode as _unbase64
    return _base64(s.encode('utf-8')).decode('utf-8')

def getNodeId(mongoId, nodeSchemaName):
    from six import text_type
    return base64(':'.join([nodeSchemaName, text_type(mongoId)]))

async def publish_relay_node_add(psap_id, id_, nodeSchemaName):
    try:
        nodeId = getNodeId(id_, nodeSchemaName)
        psap_id= str(psap_id)
        jsonData = {
            'nodeId' : nodeId,
            'schemaName': nodeSchemaName
        }
        topic = u'com.emergent911.nodeId.added.%s' % psap_id
        log.info('publishRelayNodeAdd, topic %s, data %r', topic, jsonData)

        await wamp_publish(topic, jsonData)
    except Exception as e:
        stacktrace = traceback.format_exc()
        log.error(stacktrace)
        log.error(str(e))


async def publish_relay_node_update(psap_id, id_, nodeSchemaName):
    try:
        nodeId = getNodeId(id_, nodeSchemaName)
        psap_id= str(psap_id)
        jsonData = {
            'nodeId' : nodeId,
            'schemaName': nodeSchemaName
        }
        topic = u'com.emergent911.nodeId.updated.%s' % psap_id
        log.info('publishRelayNodeUpdate, topic %s, data %r', topic, jsonData)

        await wamp_publish(topic, jsonData)
    except Exception as e:
        stacktrace = traceback.format_exc()
        log.error(stacktrace)
        log.error(str(e))


