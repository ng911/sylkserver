import logging
import traceback

from .core import wamp_publish

log = logging.getLogger('emergent-ng911')

def base64(s):
    from base64 import b64encode as _base64, b64decode as _unbase64
    return _base64(s.encode('utf-8')).decode('utf-8')


def get_node_id(mongoId, nodeSchemaName):
    from six import text_type
    return base64(':'.join([nodeSchemaName, text_type(mongoId)]))


async def publish_relay_node_new(document_json, psap_id, id_, node_schema):
    log.info('inside publish_relay_node_changed')
    node_id = get_node_id(id_, node_schema)
    psap_id = str(psap_id)
    topic = u'com.emergent911.node.new.%s' % node_schema
    json_publish_data = {
        'node_id': node_id,
        'schema_name': node_schema,
        'psap_id': psap_id,
        'document_json' : document_json
    }
    #log.info('publish_relay_node_changed, topic %s, data %r', topic, json_publish_data)
    log.info('publish_relay_node_changed, topic %s', topic)
    await wamp_publish(topic, json_publish_data, exclude_me=False)


async def publish_relay_node_changed(document_json, psap_id, id_, node_schema):
    log.info('inside publish_relay_node_changed')
    node_id = get_node_id(id_, node_schema)
    psap_id = str(psap_id)
    topic = u'com.emergent911.node.%s' % node_schema
    json_publish_data = {
        'node_id': node_id,
        'schema_name': node_schema,
        'psap_id': psap_id,
        'document_json' : document_json
    }
    #log.info('publish_relay_node_changed, topic %s, data %r', topic, json_publish_data)
    log.info('publish_relay_node_changed, topic %s', topic)
    await wamp_publish(topic, json_publish_data, exclude_me=False)


async def publish_relay_node_add(document_json, psap_id, id_, node_schema):
    try:
        '''
        nodeId = getNodeId(id_, nodeSchemaName)
        psap_id= str(psap_id)
        jsonData = {
            'nodeId' : nodeId,
            'schemaName': nodeSchemaName
        }
        topic = u'com.emergent911.nodeId.added.%s' % psap_id
        log.info('publishRelayNodeAdd, topic %s, data %r', topic, jsonData)

        await wamp_publish(topic, jsonData)
        '''
        await publish_relay_node_changed(document_json, psap_id, id_, node_schema)
        await publish_relay_node_new(document_json, psap_id, id_, node_schema)
    except Exception as e:
        stacktrace = traceback.format_exc()
        log.error(stacktrace)
        log.error(str(e))


async def publish_relay_node_update(document_json, psap_id, id_, node_schema):
    try:
        log.info("inside publish_relay_node_update")
        '''
        node_id = getNodeId(id_, nodeSchemaName)
        psap_id= str(psap_id)
        jsonData = {
            'nodeId' : nodeId,
            'schemaName': nodeSchemaName
        }
        topic = u'com.emergent911.nodeId.updated.%s' % psap_id
        '''
        await publish_relay_node_changed(document_json, psap_id, id_, node_schema)
    except Exception as e:
        stacktrace = traceback.format_exc()
        log.error(stacktrace)
        log.error(str(e))


