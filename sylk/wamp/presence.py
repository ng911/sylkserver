from twisted.internet.defer import inlineCallbacks, returnValue
try:
    from sylk.applications import ApplicationLogger
    log = ApplicationLogger(__package__)
except:
    import logging
    log = logging.getLogger('emergent-ng911')


@inlineCallbacks
def start_presence(session):
    def update_is_available(user_id, status="available"):
        from ..db.schema import User
        is_available = False
        if user_id in user_wamp_sessions:
            is_available = True
        userObj = User.objects.get(user_id=user_id)
        userObj.is_available = is_available
        if is_available:
            userObj.status = status
        else:
            userObj.status = "offline"
        userObj.save()

    def on_calltaker_status(data):
        log.info("event on_calltaker_status received")
        log.info("event on_calltaker_status received: %r", data)
        log.info("event on_calltaker_status received: %r", data['command'])
        # todo - fix , update database here
        from application.notification import IObserver, NotificationCenter, NotificationData
        global  wamp_session_client_data, user_wamp_sessions
        if data['command'] == 'status':
            wamp_session_id = str(data['wamp_session_id'])
            user_id = str(data['user_id'])
            wamp_session_client_data[wamp_session_id] = {
                "user_id" : user_id
            }
            if user_id in user_wamp_sessions:
                user_id_wamp_sessions_data = user_wamp_sessions[user_id]
                if wamp_session_id not in user_id_wamp_sessions_data:
                    user_id_wamp_sessions_data.append(wamp_session_id)
                    user_wamp_sessions[user_id] = user_id_wamp_sessions_data
            else:
                user_wamp_sessions[user_id] = [wamp_session_id]
            status = str(data['status'])
            update_is_available(user_id, status)

            log.info("process status command")
            notification_center = NotificationCenter()
            notification_data = NotificationData(username=data['username'], \
                                                  status=data['status'], wamp_session_id=data['wamp_session_id'], user_id=data['user_id'], janus_busy=data['janus_busy'])
            notification_center.post_notification('CalltakerStatus', session, notification_data)
            out = {
                'command' : 'status_updated'
            }
            session.publish(u'com.emergent.calltakers', out)
            log.info("sent status_updated")
            log.info("user_wamp_sessions %r", user_wamp_sessions)
            log.info("wamp_session_client_data %r", wamp_session_client_data)

    def on_session_leave(data):
        log.info("on_session_leave event received")
        log.info("on_session_leave event received: %r", data)
        # todo - fix , update database here
        global  wamp_session_client_data, user_wamp_sessions
        from application.notification import IObserver, NotificationCenter, NotificationData
        wamp_session_id = str(data)
        log.info("on_session_leave event received: wamp_session_client_data %r", wamp_session_client_data)
        if wamp_session_id in wamp_session_client_data:
            log.info("found wamp_session_id in wamp_session_client_data")
            client_data = wamp_session_client_data[wamp_session_id]
            user_id = client_data["user_id"]
            log.info("found user_id %r", user_id)
            del wamp_session_client_data[wamp_session_id]
            if user_id in user_wamp_sessions:
                log.info("found user_id %r in user_wamp_sessions", user_id)
                user_id_wamp_sessions_data = user_wamp_sessions[user_id]
                if wamp_session_id in user_id_wamp_sessions_data:
                    log.info("found wamp_session_id in user_id_wamp_sessions_data")
                    user_id_wamp_sessions_data.remove(wamp_session_id)
                log.info("len(user_wamp_sessions) %r", len(user_wamp_sessions))
                if len(user_id_wamp_sessions_data) == 0:
                    del user_wamp_sessions[user_id]
                else:
                    user_wamp_sessions[user_id] = user_id_wamp_sessions_data
            update_is_available(user_id)
            notification_center = NotificationCenter()
            notification_center.post_notification('CalltakerSessionLeave', session, NotificationData(wamp_session_id=data))
            out = {
                'command': 'status_updated'
            }
            session.publish(u'com.emergent.calltakers', out)

    try:
        # clear sessions and update is_available in database
        global wamp_session_client_data, user_wamp_sessions
        wamp_session_client_data = {}
        user_wamp_sessions = {}
        from ..db.calltaker import reset_calltakers_status
        from ..configuration import ServerConfig
        reset_calltakers_status(ServerConfig.psap_id)

        yield session.subscribe(on_session_leave, u'wamp.session.on_leave')
        log.info("subscribed to wamp.session.on_leave")

        res = yield session.subscribe(on_calltaker_status, u'com.emergent.calltakers')
        log.info("subscribed to topic %r, id %r", res, res.id)
        data = {
            'command' : 'send_status_update'
        }

        yield session.publish(u'com.emergent.calltakers', data)
        '''
        out = {
            'command': 'status_updated'
        }
        yield session.publish(u'com.emergent.calltakers', out)
        '''
    except Exception as e:
        log.info("exception in subscribe to topic: %r" % e)


