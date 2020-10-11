from .db import Base
from .psap import Psap
from sqlalchemy import String, Column, PickleType, DateTime, Boolean

class Client(Base):
    # human readable name, not nullable
    name = Column(String)
    # human readable description, not nullable
    description = Column(String)

    # creator of the client, not nullable
    user_id = Column(String, nullable=True, unique=False)

    client_id = Column(String, nullable=False, unique=True)
    client_secret = Column(String, nullable=False, unique=True)

    # public or confidential
    is_confidential = Column(Boolean, nullable=False, unique=False, default=True)

    _redirect_uris = Column(PickleType)
    _default_scopes = Column(PickleType)
    
    @property
    def client_type(self):
        if self.is_confidential:
            return 'confidential'
        return 'public'

    @property
    def redirect_uris(self):
        return self._redirect_uris

    @property
    def default_redirect_uri(self):
        return self.redirect_uris[0]

    @property
    def default_scopes(self):
        if self._default_scopes:
            return self._default_scopes
        return []

    @property
    def allowed_grant_types(self):
        return ['password', 'authorization_code', 'client_credentials', 'implicit']

    @property
    def user(self):
        return str(self.user_id)

    @classmethod
    def getDefaultRedirectUris(cls):
        return ['https://localhost:9000', 'https://localhost:9000/', 'https://localhost:3000', 'https://localhost:3000/']



def create_new_client(name, userid):
    client_id = str(bson.ObjectId())
    client_secret = str(bson.ObjectId())
    try:
        clientObj = Client()
        clientObj.client_secret = client_secret
        clientObj.client_id = client_id
        clientObj.name = name
        clientObj.userid = userid
        clientObj._redirect_uris = Client.getDefaultRedirectUris()
        clientObj._default_scopes = ['user', 'admin']
        clientObj.save()
        print ("created client with id %s and secret %s" % (client_id, client_secret))
    except Exception as e:
        stackTrace = traceback.format_exc()
        print ("exception in create_new_client %r" % e)
        print ("stackTrace is %s" % stackTrace)
        print ("exception in create new client %s" % e.message)


class Grant(Base):
    user_id = Column(String, nullable=True)
    client_id = Column(String, nullable=False)
    code = Column(String, nullable=False)
    redirect_uri = Column(String, nullable=True)
    expires = Column(DateTime ,nullable=True)
    _scopes = Column(PickleType)
    
    def delete(self):
        log.debug("inside grant delete")
        return Base.delete(self)

    @property
    def scopes(self):
        if self._scopes:
            return self._scopes
        return []


class Token(Base):
    token_id = ObjectIdField(unique=True)
    client_id = Column(String, nullable=False)

    user_id = Column(String, nullable=True)

    # currently only bearer is supported
    token_type = Column(String)

    access_token = Column(String, nullable=False, unique=True)
    refresh_token = Column(String, nullable=True, unique=False)
    expires = Column(DateTime ,nullable=True)
    _scopes = Column(PickleType)
    

    @property
    def scopes(self):
        if self._scopes:
            return self._scopes
        return []

    @property
    def data(self):
        TokenObj = namedtuple('TokenObj', 'id client_id user_id token_type access_token refresh_token scopes expires user')
        tokenData = TokenObj(
            id = str(self.token_id),
            client_id = self.client_id,
            user_id = self.user_id,
            token_type = self.token_type,
            access_token = self.access_token,
            refresh_token = self.refresh_token,
            scopes = self._scopes,
            expires = self.expires,
            user = User.objects.get(calltaker_id=self.user_id))
        return tokenData

