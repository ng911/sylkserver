import datetime
import bson
import os
import traceback
from flask import Flask, send_from_directory, url_for, blueprints, request, jsonify, \
    render_template, flash, abort, session, redirect
from flask_oauthlib.provider import OAuth2Provider
from flask_login import LoginManager, login_user
from flask_session import Session
import urllib
from pymongo import MongoClient
from functools import wraps

from sylk.applications import ApplicationLogger
from sylk.db.schema import Grant, Client, Token, User

log = ApplicationLogger(__package__)

from twisted.internet import reactor
from twisted.web.proxy import ReverseProxyResource
from twisted.web.resource import Resource
from twisted.web.server import Site
from twisted.web.wsgi import WSGIResource

app = Flask(__name__)
app.secret_key = 'best psap available, supercharged with webrtc'
app.config['SESSION_TYPE'] = 'mongodb'
#mongo_uri = 'mongodb://ws:kingfisher94108@ds133903-a1.mlab.com:33903/supportgenie_ws?replicaSet=rs-ds133903'
mongo_uri = 'mongodb://localhost:27017/ng911'
mongo_client = MongoClient(mongo_uri)
app.config['SESSION_MONGODB'] = mongo_client
app.config['SESSION_MONGODB_DB'] = 'ng911'
app.config['SESSION_MONGODB_COLLECT'] = 'web_sessions'

login_manager = LoginManager()
login_manager.init_app(app)

oauth = OAuth2Provider(app)


from authentication import authentication
from calltaker import calltaker

app.register_blueprint(authentication, url_prefix='/auth')
app.register_blueprint(calltaker, url_prefix='/calltaker')


log = ApplicationLogger(__package__)

'''
@app.route('/')
def index():
    return 'My Twisted Flask root'
'''

@app.route('/example')
def example():
    log.info("inside example")
    return 'My Twisted Flask example'


@app.route('/list-routes', methods=['GET', 'POST'])
def list_routes():
    response = {}
    output = []
    for rule in app.url_map.iter_rules():
        options = {}
        for arg in rule.arguments:
            options[arg] = "[{0}]".format(arg)

        methods = ','.join(rule.methods)
        url = url_for(rule.endpoint, **options)
        line = urllib.unquote("{:50s} {:20s} {}".format(rule.endpoint, methods, url))
        output.append(line)
    response['output'] = output
    return jsonify(response)


@app.route('/calltaker', methods=['GET', 'POST'])
def calltaker():
    pass

'''
# Serve React App
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    log.info('serve react app')
    log.info('path is %r' % path)

    try:
        if(path == ""):
            log.info('send index.html')
            return send_from_directory('react_app/build', 'test.html')
        else:
            if(os.path.exists("react_app/build/" + path)):
                return send_from_directory('react_app/build', path)
            else:
                return send_from_directory('react_app/build', 'index.html')
    except Exception as e:
        log.error("exception in serve %r " % e)
'''

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)



@login_manager.user_loader
def load_user(user_id):
    try:
        return User.objects.get(user_id=user_id)
    except Exception as e:
        return None


'''
start ouath related functions
'''
@oauth.clientgetter
def load_client(client_key):
    try:
        log.info("inside load client for key %r", client_key)
        client = Client.objects.get(client_id=client_key)
        log.info("inside load client returned %r, secret %r, hasattr %r", client, client.client_secret, hasattr(client, 'client_secret'))
        return client
    except Exception as e:
        log.error("inside load client exception %r", e)
        return None


@oauth.grantgetter
def load_grant(client_id, code):
    try:
        log.info("inside load_grant for client_id %r, code %r", client_id, code)
        grantObj = Grant.objects.get(client_id=client_id, code=code)
        log.info("grantObj is %r", grantObj)
        grantObj.user = grantObj.user_id
        return grantObj
    except Exception as e:
        log.error("Exception in load_grant %r", e)
        return None

def get_current_user():
    if 'userid' in session:
        return session['userid']
    return None

#from datetime import datetime, timedelta

@oauth.grantsetter
def save_grant(client_id, code, request, *args, **kwargs):
    # decide the expires time yourself

    log.info("inside save_grant for client_id %r, code %r", client_id, code)
    try:
        expires = datetime.datetime.utcnow() + datetime.timedelta(seconds=100)
        grant = Grant()
        grant.client_id=client_id
        log.info("grant.client_id is %r", grant.client_id)
        grant.code=code['code']
        log.info("grant.code is %r", grant.code)
        log.info("request.redirect_uri is %r", request.redirect_uri)
        grant.redirect_uri=request.redirect_uri
        log.info("request.scopes is %r", request.scopes)
        grant._scopes=request.scopes
        grant.user_id=get_current_user()
        log.info("grant.user_id is %r", grant.user_id)
        grant.expires=expires
        log.info("grant.expires is %r", grant.expires)
        grant.save()
        return grant
    except Exception as e:
        stackTrace = traceback.format_exc()
        log.error("exception in save_grant %r", e)
        log.error(stackTrace)



@oauth.tokengetter
def load_token(access_token=None, refresh_token=None):
    log.info("inside load_token for access_token=%r, refresh_token=%r", access_token, refresh_token)
    try:
        if access_token:
            tokenObj = Token.objects.get(access_token=access_token)
        elif refresh_token:
            tokenObj = Token.objects.get(refresh_token=refresh_token)
        tokenObj.id = tokenObj.token_id
        tokenData = tokenObj.data
        if isinstance(tokenData, dict):
            hashed_token = tuple(sorted(tokenData.items()))
        elif isinstance(tokenData, tuple):
            hashed_token = tokenData
        else:
            raise TypeError('%r is unknown type of token' % tokenData)

        log.info("got tokenObj %r, id %r, tokenData %r, hashed_token %r", tokenObj, tokenObj.id, tokenData, hashed_token)
        return tokenData
    except Exception as e:
        stackTrace = traceback.format_exc()
        log.error("error in load_token %r", e)
        log.error("stackTrace is %s", stackTrace)


@oauth.tokensetter
def save_token(token, request, *args, **kwargs):
    log.info("inside save_token for token=%r", token)
    log.info("inside save_token for request=%r", request)
    log.info("inside save_token for request.user=%r", request.user)

    try:
        toks = Token.objects(client_id=request.client.client_id,
                                     user_id=request.user)
        # make sure that every client has only one token connected to a user
        for t in toks:
            t.delete()

        expires_in = token.get('expires_in')
        expires = datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)

        tok = Token()

        tok.access_token=token['access_token']
        if 'refresh_token' in token:
            tok.refresh_token=token['refresh_token']
        else:
            # just store a random value
            tok.refresh_token = str(bson.ObjectId())
        tok.token_type=token['token_type']
        scopes=token['scope']
        log.info('scopes is %r', scopes)
        tok._scopes = scopes.split()
        log.info('tok._scopes is %r', tok._scopes)
        tok.expires=expires
        tok.token_id = bson.ObjectId()
        tok.client_id=request.client.client_id
        tok.user_id=str(request.user)
        log.info('tok.user_id is %r', tok.user_id)
        log.info('tok.client_id is %r', tok.client_id)

        tok.save()
    except Exception as e:
        stackTrace = traceback.format_exc()
        log.info("exception in save_token %r", e)
        log.info("stackTrace is %s", stackTrace)
        return None

    return tok

@oauth.usergetter
def get_user(username, password, *args, **kwargs):
    log.info("inside oauth get_user for username=%r", username)
    try:
        user = User.objects.get(loginid=username)
        if user.check_password(password):
            return user
    except Exception as e:
        pass
    return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not ('userid' in session):
            log.info("request.url is %r", request.url)
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/oauth/authorize', methods=['GET', 'POST'])
@login_required
@oauth.authorize_handler
def authorize(*args, **kwargs):
    log.info("inside oauth authorize %r", kwargs)
    log.info("*args %r, **kwargs %r     is ", args, kwargs)
    return True
    #if request.method == 'GET':
    #    client_id = kwargs.get('client_id')
    #    client = db.Client.objects.get(client_id=client_id)
    #    kwargs['client'] = client
    #    return render_template('oauthorize.html', **kwargs)

    #confirm = request.form.get('confirm', 'no')
    #return confirm == 'yes'


@app.route('/oauth/token', methods=['POST'])
@oauth.token_handler
def access_token():
    log.info("inside oauth access_token")
    return None

@app.route('/oauth/revoke', methods=['POST'])
@oauth.revoke_handler
def revoke_token():
    log.info("inside oauth revoke_token")
    pass

'''
@app.route('/getOauthUserData', methods=['GET', 'POST'])
@oauth.require_oauth('admin')
def getOauthUserData():
    try:
        user = request.oauth.user
        response = {}
        response['userid'] = str(user.userid)
        if isinstance(user, db.Agent):
            response['email'] = str(user.loginid)
            response['companyId'] = str(user.companyId)
            combanyObj = db.Company.objects.get(companyId=user.companyId)
            response['companyName'] = combanyObj.name
        else:
            response['email'] = user.email
        response['name'] = user.name
        response['photoUrl'] = user.photoUrl
        response['result'] = 'success'
        return jsonify(response)
    except Exception as e:
        stackTrace = traceback.format_exc()
        log.info("exception in getUserData %r", e)
        log.info("stackTrace is %r", stackTrace)
        response = {'result' : 'failure', 'error' : e.message}
        return jsonify(response)
'''

'''
end ouath related functions
'''


def start_server():
    flask_resource = WSGIResource(reactor, reactor.getThreadPool(), app)
    flask_site = Site(flask_resource)

    reactor.listenTCP(8081, flask_site, interface="0.0.0.0")




