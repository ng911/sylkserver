# this file implements a server to dump ALI data to clients listening for it
from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor

from sylk.configuration import ServerConfig

class AliDumpProtocol(Protocol):
    def __init__(self, factory):
        self.factory = factory

    def connectionMade(self):
        self.factory.ali_clients.append(self)

    def connectionLost(self, reason):
        self.factory.ali_clients.remove(self)


class AliDumpFactory(Factory):
    def __init__(self):
        self.ali_clients = []

    def buildProtocol(self, addr):
        return AliDumpProtocol(self)

    def dumpAli(self, stationId, rawAliData):
        for ali_client in self.factory.ali_clients:
            ali_client.transport.write('\x02')
            ali_client.transport.write(stationId)
            ali_client.transport.write(rawAliData)
            ali_client.transport.write('\x03')

def start_alidump_server():
    reactor.listenTCP(ServerConfig.alidump_port, AliDumpFactory())


