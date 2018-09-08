# this file implements a server to dump ALI data to clients listening for it
import traceback
from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor

from sipsimple.threading import run_in_twisted_thread
from sylk.configuration import ServerConfig
from sylk.applications import ApplicationLogger

ali_dump_factory = None
log = ApplicationLogger(__package__)

class AliDumpProtocol(Protocol):
    def __init__(self, factory):
        self.factory = factory

    def connectionMade(self):
        log.info('dumpAli - client connected')
        self.factory.ali_clients.append(self)

    def connectionLost(self, reason):
        log.info('dumpAli - client disconnected')
        self.factory.ali_clients.remove(self)


class AliDumpFactory(Factory):
    def __init__(self):
        self.ali_clients = []

    def buildProtocol(self, addr):
        return AliDumpProtocol(self)

    def dumpAli(self, stationId, rawAliData):
        log.info('dumpAli - for station %s, num clients %d', stationId, len(self.ali_clients))
        for ali_client in self.ali_clients:
            ali_client.transport.write('\x02')
            ali_client.transport.write(stationId)
            ali_client.transport.write(rawAliData)
            ali_client.transport.write('\x03')


def start_alidump_server():
    global ali_dump_factory
    ali_dump_factory = AliDumpFactory()
    reactor.listenTCP(ServerConfig.alidump_port, ali_dump_factory)


def dump_ali(station_id, raw_ali_data):
    if ali_dump_factory is not None:
        try:
            ali_dump_factory.dumpAli(station_id, raw_ali_data)
        except Exception as e:
            stacktrace = traceback.format_exc()
            log.error("%s", stacktrace)
            log.error("dump_ali error for , %s, %s", station_id, str(e))
    else:
        log.error("ali dump server not started?")


