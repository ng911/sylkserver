
from application.system import host
from sipsimple.account import Account, AccountManager
from sipsimple.configuration import SettingsObject
from sipsimple.configuration.datatypes import SIPAddress
from sipsimple.core import Engine, Route, SIPURI
from sylk.applications import ApplicationLogger

from sylk.configuration import SIPConfig

log = ApplicationLogger(__package__)

__all__ = 'DefaultAccount',


class DefaultContactURIFactory(object):

    def __init__(self):
        self.username = 'sylkserver'

    def __getitem__(self, key):
        if isinstance(key, tuple):
            # The first part of the key might be PublicGRUU and so on, but we don't care about
            # those here, so ignore them
            _, key = key
        if not isinstance(key, (basestring, Route)):
            raise KeyError("key must be a transport name or Route instance")

        transport = key if isinstance(key, basestring) else key.transport
        parameters = {} if transport=='udp' else {'transport': transport}
        if SIPConfig.local_ip not in (None, '0.0.0.0'):
            ip = SIPConfig.local_ip.normalized
        elif isinstance(key, basestring):
            ip = host.default_ip
        else:
            ip = host.outgoing_ip_for(key.address)
        if ip is None:
            raise KeyError("could not get outgoing IP address")
        port = getattr(Engine(), '%s_port' % transport, None)
        if port is None:
            raise KeyError("unsupported transport: %s" % transport)
        uri = SIPURI(user=self.username, host=ip, port=port)
        uri.parameters.update(parameters)
        return uri


class DefaultAccount(Account):
    """
    Subclass of Account which doesn't start any subsystem. SylkServer just
    uses it as the default account for all applications as a settings object.
    """

    __id__ = SIPAddress('default@sylkserver')

    id = property(lambda self: self.__id__)
    enabled = True

    def __new__(cls):
        with AccountManager.load.lock:
            if not AccountManager.load.called:
                raise RuntimeError("cannot instantiate %s before calling AccountManager.load" % cls.__name__)
            return SettingsObject.__new__(cls)

    def __init__(self):
        super(DefaultAccount, self).__init__('default@sylkserver')
        self.contact = DefaultContactURIFactory()

    @property
    def uri(self):
        return SIPURI(user=self.user, host=SIPConfig.local_ip.normalized)

    def _activate(self):
        pass

    def _deactivate(self):
        pass




def some_func(self, arg1):
    print(arg1)

@classmethod
def new_account_func(cls, test):
    log.info("new_account_func test is %r", test)
    with AccountManager.load.lock:
        if not AccountManager.load.called:
            raise RuntimeError("cannot instantiate %s before calling AccountManager.load" % cls.__name__)
        return SettingsObject.__new__(cls)

def get_user_account_class(username):
    def constructor(self):
        Account.__init__(self, self.sip_address)
        self.contact = DefaultContactURIFactory()

    def _activate(self):
        pass

    def _deactivate(self):
        pass

    sip_address = "%r@sylkserver" % username
    return type(username + "UserAccountClass", (Account,), {
        "sip_address" : sip_address,
        'user' : username,
        "__id__": SIPAddress(sip_address),
        "id": property(lambda self: self.__id__),
        "__init__": constructor,
        "uri":property(lambda self: SIPURI(user=self.user, host=SIPConfig.local_ip.normalized)),
        "enabled": True,
        "_activate": _activate,
        "_deactivate": _deactivate,
        "__new__": new_account_func
    })

def get_user_account(username):
    UserAccountClass = get_user_account_class(username)
    return UserAccountClass()

