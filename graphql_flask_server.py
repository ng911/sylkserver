#!/usr/bin/env python
import sys
import logging
from twisted.internet import reactor

import sylk.graphql
from sylk import __version__

logger = logging.getLogger('ng911')


def setup_logger(name, logger):
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler = logging.FileHandler("%s.log" % name)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    streamHandler = logging.StreamHandler()
    streamHandler.setLevel(logging.DEBUG)
    # create formatter and add it to the handlers
    streamHandler.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(streamHandler)


if __name__ == '__main__':
    name = 'graphql-server'
    setup_logger(name, logger)

    fullname = 'emergent ng911 graphql server'
    logger.info('Starting {name} {version}'.format(name=fullname, version=__version__))

    try:
        sylk.graphql.start_server()
        reactor.run()
    except Exception as e:
        logger.fatal('Failed to start {name}: {exception!s}'.format(name=fullname, exception=e))
        logger.exception()
        sys.exit(1)



