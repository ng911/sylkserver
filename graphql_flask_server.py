#!/usr/bin/env python
import sys
import logging

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
    name = 'graphql-server'
    setup_logger(name, log)

    from sylk import __version__

    fullname = 'emergent ng911 graphql server'
    log.info('Starting {name} {version}'.format(name=fullname, version=__version__))

    try:
        import sylk.graphql
        import asyncio
        from sylk.wamp_asyncio import start
        start()
        sylk.graphql.start_server()
    except Exception as e:
        log.fatal('Failed to start {name}: {exception!s}'.format(name=fullname, exception=e))
        log.exception(str(e))
        sys.exit(1)



