
from application.configuration import ConfigSection, ConfigSetting
from application.configuration.datatypes import NetworkRangeList, StringList
from application.system import host
from sipsimple.configuration.datatypes import NonNegativeInteger, SampleRate

from sylk.configuration.datatypes import AudioCodecs, IPAddress, Path, Port, PortRange, SIPProxyAddress, SRTPEncryption, LogLevel
from sylk.resources import Resources, VarResources
from sylk.tls import Certificate, PrivateKey


class ServerConfig(ConfigSection):
    __cfgfile__ = 'config.ini'
    __section__ = 'Server'

    ca_file = ConfigSetting(type=Path, value=Path(Resources.get('tls/ca.crt')))
    certificate = ConfigSetting(type=Path, value=Path(Resources.get('tls/default.crt')))
    verify_server = False
    enable_bonjour = False
    default_application = 'conference'
    psap_id = ""
    sop_dir = "sop"
    asterisk_server = "127.0.0.1:5090"
    outgoing_gateway = "127.0.0.1:5090"
    wamp_crossbar_server = u"ws://127.0.0.1:8080/ws"
    db_connection = "mongodb://localhost:27017/"
    full_db_connection = "mongodb://localhost:27017/"
    ali_link1_ip = "165.227.16.153"
    ali_link1_port = 11010
    ali_link1_format = "30WWireless"
    ali_link2_ip = "159.65.73.31"
    ali_link2_port = 11010
    ali_link2_format = "30WWireless"
    ali_link3_ip = ""
    ali_link3_port = ""
    ali_link3_format = ""
    ali_link4_ip = ""
    ali_link4_port = ""
    ali_link4_format = ""
    db_name = "ng911"
    db_user = ""
    db_pwd = ""
    from_number = "911"
    alidump_port = 12010
    alidump_client_host = ""
    alidump_client_port = ""
    application_map = ConfigSetting(type=StringList, value=['echo:echo'])
    disabled_applications = ConfigSetting(type=StringList, value='')
    extra_applications_dir = ConfigSetting(type=Path, value=None)
    trace_dir = ConfigSetting(type=Path, value=Path(VarResources.get('log/sylkserver')))
    trace_dns = False
    trace_sip = False
    trace_msrp = False
    trace_core = False
    trace_notifications = False
    log_level = ConfigSetting(type=LogLevel, value=LogLevel('info'))
    spool_dir = ConfigSetting(type=Path, value=Path(VarResources.get('spool/sylkserver')))


class SIPConfig(ConfigSection):
    __cfgfile__ = 'config.ini'
    __section__ = 'SIP'

    local_ip = ConfigSetting(type=IPAddress, value=IPAddress(host.default_ip))
    local_udp_port = ConfigSetting(type=Port, value=5060)
    local_tcp_port = ConfigSetting(type=Port, value=5060)
    local_tls_port = ConfigSetting(type=Port, value=5061)
    advertised_ip = ConfigSetting(type=IPAddress, value=None)
    outbound_proxy = ConfigSetting(type=SIPProxyAddress, value=None)
    trusted_peers = ConfigSetting(type=NetworkRangeList, value=NetworkRangeList('any'))
    enable_ice = False


class MSRPConfig(ConfigSection):
    __cfgfile__ = 'config.ini'
    __section__ = 'MSRP'

    use_tls = True


class RTPConfig(ConfigSection):
    __cfgfile__ = 'config.ini'
    __section__ = 'RTP'

    audio_codecs = ConfigSetting(type=AudioCodecs, value=['opus', 'G722', 'speex', 'PCMA', 'PCMU'])
    port_range = ConfigSetting(type=PortRange, value=PortRange('50000:50500'))
    srtp_encryption = ConfigSetting(type=SRTPEncryption, value='opportunistic')
    timeout = ConfigSetting(type=NonNegativeInteger, value=30)
    sample_rate = ConfigSetting(type=SampleRate, value=48000)


class WebServerConfig(ConfigSection):
    __cfgfile__ = 'config.ini'
    __section__ = 'WebServer'

    local_ip = ConfigSetting(type=IPAddress, value=IPAddress(host.default_ip))
    local_port = ConfigSetting(type=Port, value=10888)
    hostname = ''
    certificate = ConfigSetting(type=Path, value=None)
    certificate_chain = ConfigSetting(type=Path, value=None)


class ThorNodeConfig(ConfigSection):
    __cfgfile__ = 'config.ini'
    __section__ = 'ThorNetwork'

    enabled = False
    domain = "sipthor.net"
    multiply = 1000
    certificate = ConfigSetting(type=Certificate, value=None)
    private_key = ConfigSetting(type=PrivateKey, value=None)
    ca = ConfigSetting(type=Certificate, value=None)
