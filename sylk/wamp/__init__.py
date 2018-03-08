from autobahn.twisted.component import Component
from sylk.applications import ApplicationLogger
from application.notification import IObserver, NotificationCenter, NotificationData
from sylk.utils import dump_object_member_vars, dump_object_member_funcs
log = ApplicationLogger(__package__)
from twisted.internet.defer import inlineCallbacks, returnValue
from sylk.data.calltaker import CalltakerData

log.info("wamp session start")

comp = Component(
     transports=u"ws://159.65.73.31:8080/ws",
     realm=u"realm1",
     extra="tarun"
 )


@comp.on_join
@inlineCallbacks
def joined(session, details):
    log.info("wamp session ready %r, id %r", session, session._session_id)
    # make sure calltaker is initialized
    CalltakerData()

    def on_calltaker_status(data):
        log.info("event on_calltaker_status received")
        log.info("event on_calltaker_status received: %r", data)
        log.info("event on_calltaker_status received: %r", data['command'])
        '''
        if data['command'] == 'status':
            notification_center = NotificationCenter()
            notification_center.post_notification('CalltakerStatus', session, NotificationData(username=data['username'], \
                                                  status=data['status'], wamp_session_id=data['wamp_session_id'], user_id=data['user_id']))
            data = {
                'command' : 'status_updated'
            }
            yield session.publish(u'com.emergent.calltakers', data)
            log.info("sent status_updated")
        '''

    def on_session_leave(data):
        log.info("on_session_leave event received")
        log.info("on_session_leave event received: %r", data)
        notification_center = NotificationCenter()
        notification_center.post_notification('CalltakerSessionLeave', session, NotificationData(wamp_session_id=data))

    try:
        yield session.subscribe(on_session_leave, u'wamp.session.on_leave')
        log.info("subscribed to wamp.session.on_leave")

        res = yield session.subscribe(on_calltaker_status, u'com.emergent.calltakers')
        log.info("subscribed to topic %r, id %r", res, res.id)
        data = {
            'command' : 'send_status_update'
        }
        yield session.publish(u'com.emergent.calltakers', data)

    except Exception as e:
        log.info("exception in subscribe to topic: %r" % e)
    '''
    dump_object_member_vars(log, session)
    dump_object_member_funcs(log, session)
    log.info("wamp session id %r" % session._session_id)
    log.info("wamp confog %r" % session.config)
    dump_object_member_vars(log, session.config)
    dump_object_member_funcs(log, session.config)
    log.info("wamp config extra %r" % session.config.extra)
    '''

def start():
     comp.start()
