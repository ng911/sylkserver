import traceback
from flask import session, app, redirect, url_for, request, flash, render_template, abort, Blueprint
from flask_login import LoginManager, login_user
from flask_wtf import Form
from wtforms import StringField, PasswordField, SubmitField, HiddenField, BooleanField
from wtforms import validators, ValidationError

from utils import get_argument, is_safe_url
from mongoengine import DoesNotExist
from sylk.applications import ApplicationLogger
from sylk.db.schema import Grant, Client, Token, User, CalltakerStation

authentication = Blueprint('authentication', __name__,
                        template_folder='templates')


log = ApplicationLogger(__package__)



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
            user = User.objects.get(username = self.username.data)
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

            try:
                log.info("Logged in redirecting to %r", url_for('/'))
            except Exception as e:
                log.error("login redirecting debug %r", e)

            session['user_id'] = str(form.user.user_id)

            # we create an oauth access tokem and store it in the session to be used by the client
            # the client can access it using the session cookie
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
    station_id = ''
    log_level = ''
    if 'user_id' in session:
        user_id = session['user_id']
        if (user_id is not None) and (user_id != ''):
            user_obj = User.objects.get(user_id=user_id)
            username = user_obj.username
            ip_address = request.remote_addr
            log.info("session_info ip_address is %r", ip_address)
            try:
                station_db_obj = CalltakerStation.objects.get(ip_address=ip_address)
                user_obj.station_id = station_db_obj.station_id
                if hasattr(station_db_obj, 'station_id') and (station_db_obj.station_id != None):
                    station_id = station_db_obj.station_id
                if hasattr(station_db_obj, 'log_level') and (station_db_obj.log_level != None):
                    log_level = station_db_obj.log_level
                user_obj.save()
            except:
                pass
    return render_template('session-info.js', initial_data={'user_id' : user_id, 'username' : username, 'station_id' : station_id, 'log_level' : log_level})


@authentication.route('/logout', methods=['GET', 'POST'])
def logout():
    try:
        log.info("inside logout for user")
        next = get_argument('next', '')
        if 'user_id' in session:
            del session['user_id']
        if 'username' in session:
            del session['username']
        redirect_uri = url_for('.login', _external=True, next=next)
        log.info("inside logout done , redirect to %r", redirect_uri)
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



