'''
Start of OAuth related db models
'''
import logging
import traceback
from collections import namedtuple
import bson
from mongoengine import *
from .user import User

log = logging.getLogger("emergent-ng911")


class Client(Document):
    # human readable name, not required
    name = StringField()
    # human readable description, not required
    description = StringField()

    # creator of the client, not required
    user_id = StringField(required=False, unique=False)

    client_id = StringField(required=True, unique=True)
    client_secret = StringField(required=True, unique=True)

    # public or confidential
    is_confidential = BooleanField(required=True, unique=False, default=True)

    _redirect_uris = ListField(StringField(), required=True, unique=False, default=[])
    _default_scopes = ListField(StringField(), required=True, unique=False, default=[])
    meta = {
        'indexes': [
            'client_id',
            'client_secret'
        ],
    }

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


class Grant(Document):
    user_id = StringField(required=False)
    client_id = StringField(required=True)
    code = StringField(required=True)
    redirect_uri = StringField(required=False)
    expires = DateTimeField(required=False)
    _scopes = ListField(StringField())
    meta = {
        'indexes': [
            'code',
            'client_id',
            'user_id'
        ],
    }

    def delete(self):
        log.debug("inside grant delete")
        return Document.delete(self)

    @property
    def scopes(self):
        if self._scopes:
            return self._scopes
        return []


class Token(Document):
    token_id = ObjectIdField(unique=True)
    client_id = StringField(required=True)

    user_id = StringField(required=False)

    # currently only bearer is supported
    token_type = StringField()

    access_token = StringField(required=True, unique=True)
    refresh_token = StringField(required=False, unique=False)
    expires = DateTimeField(required=False)
    _scopes = ListField(StringField())
    meta = {
        'indexes': [
            'id',
            'client_id',
            'user_id'
        ],
    }

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


'''
End of OAuth related db models
'''
