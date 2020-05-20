#!/usr/bin/env python
import sys
import logging
import traceback

from twisted.internet import reactor

log = logging.getLogger('emergent-ng911')


def setup_logger(name, log):
    log.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler = logging.FileHandler("%s.log" % name)
    handler.setFormatter(formatter)
    log.addHandler(handler)

    streamHandler = logging.StreamHandler()
    streamHandler.setLevel(logging.DEBUG)
    # create formatter and add it to the handlers
    streamHandler.setFormatter(formatter)
    # add the handlers to the logger
    log.addHandler(streamHandler)


if __name__ == '__main__':
    name = 'rest-server'
    setup_logger(name, log)

    from sylk import __version__

    fullname = 'emergent ng911 rest api server'
    log.info('Starting {name} {version}'.format(name=fullname, version=__version__))

    try:
        from sylk.api import start_rest_api_server

        start_rest_api_server()
        reactor.run()
    except Exception as e:
        stacktrace = traceback.format_exc()
        log.fatal('Failed to start {name}: {exception!s}'.format(name=fullname, exception=e))
        log.error(stacktrace)
        #log.exception(e.message)
        sys.exit(1)


