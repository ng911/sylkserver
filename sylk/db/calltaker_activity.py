from .schema import CalltakerActivity, User

def add_logged_in(user_id):
    activityObj = CalltakerActivity(user_id=user_id, event='login')
    activityObj.save()

def add_logged_out(user_id):
    activityObj = CalltakerActivity(user_id=user_id, event='logout')
    activityObj.save()

def add_call_pickup(user_id, response_time):
    activityObj = CalltakerActivity(user_id=user_id, event='answer_call')
    activityObj.event_num_data = response_time
    activityObj.save()

def add_call_pickup_by_name(username, response_time):
    userObj = User.objects.get(username=username)
    add_call_pickup(str(userObj.user_id), response_time)

def add_call_hangup(user_id):
    activityObj = CalltakerActivity(user_id=user_id, event='hangup')
    activityObj.save()

def add_call_hangup_by_name(username):
    userObj = User.objects.get(username=username)
    add_call_hangup(str(userObj.user_id))





