from .schema import CalltakerActivity, User

def add_logged_in(user_id, psap_id):
    activityObj = CalltakerActivity(user_id=user_id, event='login', psap_id=psap_id)
    activityObj.save()

def add_logged_out(user_id, psap_id):
    activityObj = CalltakerActivity(user_id=user_id, event='logout', psap_id=psap_id)
    activityObj.save()

def add_call_pickup(user_id, response_time, psap_id):
    activityObj = CalltakerActivity(user_id=user_id, event='answer_call', psap_id=psap_id)
    activityObj.event_num_data = response_time
    activityObj.save()

def add_call_pickup_by_name(username, response_time, psap_id):
    userObj = User.objects.get(username=username, psap_id=psap_id)
    user_id = str(userObj.user_id)
    add_call_pickup(user_id, response_time, psap_id)

def add_call_hangup(user_id, psap_id):
    activityObj = CalltakerActivity(user_id=user_id, event='hang_up', psap_id=psap_id)
    activityObj.save()

def add_call_hangup_by_name(username, psap_id):
    userObj = User.objects.get(username=username, psap_id=psap_id)
    user_id = str(userObj.user_id)
    add_call_hangup(user_id, psap_id)





