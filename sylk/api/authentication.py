import traceback
import logging

from flask import session, app, redirect, url_for, request, flash, render_template, abort, Blueprint, jsonify
from flask_login import LoginManager, login_user
from flask_wtf import Form
from wtforms import StringField, PasswordField, SubmitField, HiddenField, BooleanField
from wtforms import validators, ValidationError
from flask_cors import CORS

from .utils import get_argument, is_safe_url
from .decorators import check_exceptions
from ..db.schema import Grant, Client, Token, User, CalltakerStation
from ..db.psap import get_psap_from_domain

from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token, create_refresh_token, jwt_refresh_token_required,
    get_jwt_identity
)
from ..db.calltaker_activity import add_logged_in, add_logged_out

authentication = Blueprint('authentication', __name__,
                        template_folder='templates')
CORS(authentication)


log = logging.getLogger("emergent-ng911")

jwt = None

def setjwt(value):
    print(value)
    global jwt
    jwt = value


'''
start Flask-Login related functions
'''
def get_redirect_target():
    log.info("in get_redirect_target")
    for target in request.args.get('next'), request.referrer:
        log.info("found target %r", target)
        if not target:
            continue
        if is_safe_url(target):
            return target
        else:
            log.info("target %r not safe  ignoring", target)
            return target


class LoginForm(Form):
    next = HiddenField()
    username = StringField("username", [validators.DataRequired("Please enter user name.")])

    password = PasswordField("password", [validators.DataRequired("Please enter password.")])
    rememberMe = BooleanField(id="remember-me", label="Remember Me")
    #submit = SubmitField("login", class_="btn btn-lg btn-primary btn-block btn-signin")
    submit = SubmitField("Sign In")

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)
        if not self.next.data:
            self.next.data = get_redirect_target() or '/'

    def validate_on_submit(self):
        log.info("inside Form.validate")
        rv = self.validate()
        log.info("inside Form.validate after rv is %r", rv)

        if not rv:
            log.info("inside Form.validate after failed")
            return False

        try:
            log.info("inside Form.validate for username %r", self.username.data)

            domain_name = request["Host"]
            psap_id = get_psap_from_domain(domain_name)

            user = User.objects.get(username = self.username.data, psap_id=psap_id)
            if user is None:
                self.username.errors.append('Unknown username')
                return False

            log.info("inside Form.validate check_password %r" % self.password.data)
            if not user.check_password(self.password.data):
                self.password.errors.append('Invalid password')
                return False

            log.info("inside Form.validate check_password done")
            self.user = user
            log.info("inside Form.validate all good")
        except Exception as e:
            log.error("inside Form.validate exception %r", e)
            self.username.errors.append('invalid username or password')
            return False

        return True


@authentication.route('/refresh', methods = ['POST'])
@jwt_refresh_token_required
@check_exceptions
def refresh():
    current_user = get_jwt_identity()
    log.info('current user %r', current_user)
    access_token = create_access_token(identity = current_user)
    return (jsonify({'access_token':access_token}))


@authentication.route('/login', methods=['GET', 'POST'])
def login():
    # Here we use a class of some kind to represent and validate our
    # client-side form data. For example, WTForms is a library that will
    # handle this for us, and we use a custom LoginForm to validate.
    log.info("Inside login")
    form = LoginForm()

    if request.method == 'POST':
        log.info("validate login form")
        if form.validate_on_submit():
            log.info("login form validated")
            # Login and validate the user.
            # user should be an instance of your `User` class
            login_user(form.user, remember=form.rememberMe.data)

            log.info("Logged in successfully")
            log.info("remember me is %r", form.rememberMe.data)

            next = form.next.data
            log.info("next is %r", next)
            flash('Logged in successfully.')
            # is_safe_url should check if the url is safe for redirects.
            # See http://flask.pocoo.org/snippets/62/ for an example.
            if not is_safe_url(next):
                log.info("url not safe %r", next)
                # for testing ignore for now
                #return abort(400)

            #try:
            #    log.info("Logged in redirecting to %r", url_for('/'))
            #except Exception as e:
            #    log.error("error in login redirecting debug %r", e)

            userObj = {'email': form.user.username, 'psap_id' : form.user.psap_id, 'roles': form.user.roles}
            access_token = create_access_token(identity=userObj)
            refresh_token = create_refresh_token(identity=userObj)
            session['access_token'] = access_token
            session['refresh_token'] = refresh_token
            session['user_id'] = str(form.user.user_id)
            session['psap_id'] = str(form.user.psap_id)

            # we create an oauth access tokem and store it in the session to be used by the client
            # the client can access it using the session cookie

            add_logged_in(str(form.user.user_id), str(form.user.psap_id))
            return redirect(next or url_for('/'))

    return render_template('login.html', form=form)


@authentication.route('/session-info.js', methods=['GET'])
def session_info():
    # Here we use a class of some kind to represent and validate our
    # client-side form data. For example, WTForms is a library that will
    # handle this for us, and we use a custom LoginForm to validate.
    log.info("session_info")
    user_id = ''
    username = ''
    layout = None
    if 'user_id' in session:
        user_id = session['user_id']
        if (user_id is not None) and (user_id != ''):
            try:
                user_obj = User.objects.get(user_id=user_id)
                username = user_obj.username
                psap_id = str(user_obj.psap_id)
                ip_address = request.remote_addr
                if hasattr(user_obj, 'layout'):
                    layout = user_obj.layout
                log.info("session_info ip_address is %r", ip_address)
                try:
                    station_db_obj = CalltakerStation.objects.get(ip_address=ip_address)
                    user_obj.station_id = station_db_obj.station_id
                    user_obj.save()
                except:
                    pass
            except:
                pass
    initial_data = {'user_id': user_id, 'username': username, 'psap_id' : psap_id, 'layout' : layout}
    if 'access_token' in session:
        log.debug("found access_token in session")
        initial_data['access_token'] = session['access_token']
    if 'refresh_token' in session:
        log.debug("found refresh_token in session")
        initial_data['refresh_token'] = session['refresh_token']
    return render_template('session-info.js', initial_data=initial_data)


@authentication.route('/logout', methods=['GET', 'POST'])
def logout():
    try:
        log.info("inside logout for user")
        next = get_argument('next', '')
        user_id = None
        psap_id = None
        if 'user_id' in session:
            user_id = session['user_id']
            del session['user_id']
        if 'psap_id' in session:
            psap_id = session['psap_id']
            del session['psap_id']
        if 'username' in session:
            del session['username']
        if 'access_token' in session:
            del session['access_token']
        if 'refresh_token' in session:
            del session['refresh_token']
        redirect_uri = url_for('.login', _external=True, next=next)
        log.info("inside logout done , redirect to %r", redirect_uri)
        if user_id != None and psap_id != None:
            add_logged_out(user_id, psap_id)
        return redirect(redirect_uri)
    except Exception as e:
        stackTrace = traceback.format_exc()
        log.error("Exception in logout %r", e)
        log.error("Exception is %r", stackTrace)
        abort(500)


'''
@app.route('/login', methods=['PUT', 'POST'])
def login():
    try:
        username = get_argument('username')
        password = get_argument('password')
        next = redirect_url()

        user_obj = User.objects.get(username=username)

        if user_obj.check_password(password):
            session['user_id'] = user_obj.user_id
            redirect_url(next)
        else:
            pass
    except DoesNotExist as e:
        pass
    except Exception as e:
        pass
'''



