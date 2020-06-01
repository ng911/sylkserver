import pandas as pd
import arrow
from datetime import datetime, timedelta
from pymongo import MongoClient
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader('.'))
template = env.get_template("myreport.html")


def _connect_mongo(host, db, replicaset, username, password):
    """ A util for making a connection to mongo """

    if username and password:
        mongo_uri = 'mongodb://%s:%s@%s/%s?replicaSet=%s' % (username, password, host, db, replicaset)
        conn = MongoClient(mongo_uri)
    else:
        conn = MongoClient(host)

    return conn[db]


def read_mongo(db, collection, query={}, host='localhost', replicaset="", username=None, password=None, no_id=True):
    """ Read from Mongo and Store into DataFrame """

    # Connect to MongoDB
    db = _connect_mongo(host=host, db=db, replicaset=replicaset, username=username, password=password)

    # Make a query to the specific DB and Collection
    cursor = db[collection].find(query)

    # Expand the cursor and construct the DataFrame
    df = pd.DataFrame(list(cursor))

    # Delete the _id
    if no_id:
        del df['_id']

    return df

'''
old functions
# complex is mongoengine ComplexDateTimeField
def get_now_complex_time():
    utcnow = arrow.utcnow()
    return str(utcnow.format('YYYY,MM,DD,HH,mm,ss,SSSSSS'))


def get_last_month_complex_time():
    lastmonth = arrow.utcnow().shift(days=-9, months=-1)
    return str(lastmonth.format('YYYY,MM,DD,HH,mm,ss,SSSSSS'))

def get_start_time_arrow():
    #start_time = arrow.utcnow().shift(days=-17, months=-2)
    str_time = '2019/09/01 00:00:00'
    tz = 'UTC'
    return arrow.get(str_time, 'YYYY/M/D HH:mm:ss').replace(tzinfo=tz)

def get_end_time_arrow():
    str_time = '2019/10/01 00:00:00'
    tz = 'UTC'
    return arrow.get(str_time, 'YYYY/M/D HH:mm:ss').replace(tzinfo=tz)

def get_start_complex_time():
    start_time = get_start_time_arrow()
    return str(start_time.format('YYYY,MM,DD,HH,mm,ss,SSSSSS'))

def get_end_complex_time():
    end_time = get_end_time_arrow()
    return str(end_time.format('YYYY,MM,DD,HH,mm,ss,SSSSSS'))

def get_start_complex_time_display():
    start_time = get_start_time_arrow()
    return str(start_time.format('MMM D, YYYY h:mma'))

def get_end_complex_time_display():
    end_time = get_end_time_arrow()
    return str(end_time.format('MMM D, YYYY h:mma'))

def get_now_time_display():
    utcnow = arrow.utcnow()
    return str(utcnow.format('MMM D, YYYY h:mma'))

def get_last_month_time_display():
    lastmonth = arrow.utcnow().shift(months=-1)
    return str(lastmonth.format('MMM D, YYYY h:mma'))
'''
def get_complex_time(dateval):
    return dateval.strftime("%Y,%m,%d,%H,%M,%S,%f")

def get_time_display(dateval):
    return dateval.strftime("%b %-d, %Y %H:%M")

def get_start_of_month(dateval=datetime.today()):
    today = dateval.replace(day=1,hour=0,minute=0,second=0, microsecond=0)
    return today

def get_start_end_times():
    endDate = get_start_of_month()
    startDate = endDate - timedelta(days=1)
    startDate = get_start_of_month(startDate)
    return startDate, endDate

def get_start_end_complex_times():
    startDate, endDate = get_start_end_times()
    return get_complex_time(startDate), get_complex_time(endDate)

def get_start_end_times_display():
    startDate, endDate = get_start_end_times()
    return get_time_display(startDate), get_time_display(endDate)

def get_all_sos_calls_last_month_df(host, db, replicaset, username, password):
    start_time, end_time = get_start_end_complex_times()
    df = read_mongo(host=host, db=db, replicaset=replicaset, username=username, password=password, collection='conference',
                    query={'direction': 'in', "start_time": {"$gte": start_time}, "start_time": {"$lte": end_time}} )
    return df


def get_abandoned_sos_calls_last_month_df(host, db, replicaset, username, password):
    start_time, end_time = get_start_end_complex_times()
    df = read_mongo(host=host, db=db, replicaset=replicaset, username=username, password=password, collection='conference',
                    query={'direction': 'in', 'status': 'abandoned',
                         "start_time": {"$gte": start_time, "$lte": end_time}} )
    return df


def get_completed_sos_calls_last_month_df(host, db, replicaset, username, password):
    start_time, end_time = get_start_end_complex_times()
    #df = read_mongo(host=host, db=db, replicaset=replicaset, username=username, password=password, collection='conference', query={'direction': 'in', 'status': 'closed',
    #                                 "start_time": {"$gte": get_start_complex_time()}, "start_time": {"$lte": get_end_complex_time()}} )
    df = read_mongo(host=host, db=db, replicaset=replicaset, username=username, password=password, collection='conference', query={'direction': 'in', 'status': 'closed',
                                     "start_time": {"$gte": start_time, "$lte": end_time} } )
    return df


def get_incoming_link_df(host, db, replicaset, username, password):
    df = read_mongo(host=host, db=db, replicaset=replicaset, username=username, password=password, collection='incoming_link', query={})
    return df

def get_call_calltakers_df(host, db, replicaset, username, password):
    df = read_mongo(host=host, db=db, replicaset=replicaset, username=username, password=password, collection='conference_participant', query={'is_calltaker' : True})
    return df

def format_date(str_date):
    # print ("inside format_date for %r" % str_date)
    arrow_date = arrow.get(str_date, 'YYYY,MM,DD,HH,mm,ss,SSSSSS')
    return arrow_date.format('MMM D h:mma')


def format_orig_type(orig_type):
    if orig_type == 'sos_wireless':
        return "Wireless"
    return "Wireline"


def format_secs(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if seconds < 60:
        return "%s secs" % seconds
    if h == 0:
        return "%s mins" % int(m)
    return "%s hr, %s mins" % (h, m)

def format_mins_secs(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if seconds < 60:
        return "%s secs" % seconds
    if h == 0:
        return "%s mins %s secs" % (int(m), int(s))
    return "%s hr, %s mins" % (h, m)

def get_response_time(start_time, answer_time, status):
    if status == "closed":
        arrow_answer_time = arrow.get(answer_time, 'YYYY,MM,DD,HH,mm,ss,SSSSSS')
        arrow_start_time = arrow.get(start_time, 'YYYY,MM,DD,HH,mm,ss,SSSSSS')
        duration = arrow_answer_time - arrow_start_time

        #return format_secs(duration.seconds)
        return int(duration.seconds)
    return 0

def get_response_time_val(start_time, answer_time, status):
    if status == "closed":
        arrow_answer_time = arrow.get(answer_time, 'YYYY,MM,DD,HH,mm,ss,SSSSSS')
        arrow_start_time = arrow.get(start_time, 'YYYY,MM,DD,HH,mm,ss,SSSSSS')
        duration = arrow_answer_time - arrow_start_time

        return duration.seconds
    return 0

def get_duration(start_time, end_time):
    arrow_answer_time = arrow.get(end_time, 'YYYY,MM,DD,HH,mm,ss,SSSSSS')
    arrow_start_time = arrow.get(start_time, 'YYYY,MM,DD,HH,mm,ss,SSSSSS')
    duration = arrow_answer_time - arrow_start_time

    #return format_secs(duration.seconds)
    return int(duration.seconds)

def get_duration_val(start_time, end_time):
    arrow_end_time = arrow.get(end_time, 'YYYY,MM,DD,HH,mm,ss,SSSSSS')
    arrow_start_time = arrow.get(start_time, 'YYYY,MM,DD,HH,mm,ss,SSSSSS')
    duration = arrow_end_time - arrow_start_time

    return duration.seconds

def get_location_df(host, db, replicaset, username, password):
    df = read_mongo(host=host, db=db, replicaset=replicaset, username=username, password=password, collection='location', query={})
    #df['location_display'] = map(format_location_display, df["postal"], df["community"], df["state"])
    df['location_display'] = df.apply(lambda row: format_location_display(row.postal, row.community, row.state))
    df = df.set_index('room_number')
    return df


def format_location_display(postal, community, state):
    return "%s, %s, %s" % (postal.rstrip(), community.rstrip(), state.rstrip())


def get_abandoned_calls_report_df(host, db, replicaset, username, password):
    df_incoming_link = get_incoming_link_df(host, db, replicaset, username, password)
    df_calls = get_abandoned_sos_calls_last_month_df(host, db, replicaset, username, password)
    #df_calls['response_time'] = map(get_response_time, df_calls["start_time"], df_calls["answer_time"],
    #                                df_calls["status"])
    #df_calls['answer_time'] = df_calls['answer_time'].apply(format_date)
    df_calls['start_time'] = df_calls['start_time'].apply(format_date)

    df_missed_calls = df_calls.set_index('link_id').join(df_incoming_link.set_index('link_id'), on='link_id',
                                                         lsuffix='_caller', rsuffix='_other')
    df_missed_calls = df_missed_calls.set_index('room_number')

    #df_location = get_location_df(host, db, replicaset, username, password)
    #df_missed_calls = df_missed_calls.join(df_location, on='room_number', lsuffix='_caller', rsuffix='_other')

    #df_missed_calls = df_missed_calls.filter(items=['orig_type', 'start_time', 'caller_ani', 'location_display'])
    df_missed_calls = df_missed_calls.filter(items=['orig_type', 'start_time', 'caller_ani'])
    df_missed_calls['orig_type'] = df_missed_calls['orig_type'].apply(format_orig_type)
    #df_missed_calls.columns = ['Origination', 'Start Time', 'Caller', 'Location']
    df_missed_calls.columns = ['Origination', 'Start Time', 'Caller']
    df_missed_calls.index.names = ['Call Id']

    return df_missed_calls


def get_completed_calls_report_df(host, db, replicaset, username, password):
    print("inside get_completed_calls_report_df")
    df_incoming_link = get_incoming_link_df(host, db, replicaset, username, password)
    print("got df_incoming_link")
    df_calls = get_completed_sos_calls_last_month_df(host, db, replicaset, username, password)
    print("got df_calls")
    df_calls['response_time'] = df_calls.apply(lambda row: get_response_time(row.start_time, row.answer_time,
                                                                                   row.status), axis=1)
    df_calls['response_time_val'] = df_calls.apply(lambda row: get_response_time_val(row.start_time, row.answer_time,
                                                                                   row.status), axis=1)
    #df_calls['duration'] = map(get_duration, (df_calls["start_time"], df_calls["end_time"]))
    df_calls['duration'] = df_calls.apply(lambda row: get_duration(row.start_time, row.end_time), axis=1)
    df_calls['duration_val'] = df_calls.apply(lambda row: get_duration_val(row.start_time, row.end_time), axis=1)
    df_calls['answer_time'] = df_calls['answer_time'].apply(format_date)
    df_calls['start_time'] = df_calls['start_time'].apply(format_date)

    df_calls = df_calls.set_index('link_id').join(df_incoming_link.set_index('link_id'), on='link_id',
                                                  lsuffix='_caller', rsuffix='_other')
    df_calls = df_calls.set_index('room_number')

    df_calltakers_in_call = get_call_calltakers_df(host, db, replicaset, username, password)
    print(df_calltakers_in_call.columns.values)
    df_calls = df_calls.join(df_calltakers_in_call.set_index('room_number'), on='room_number',
                                                  lsuffix='_call', rsuffix='_calltaker')
    print(df_calls.columns.values)

    df_avg_response_time = df_calls[['response_time_val']].mean(skipna = True)
    df_avg_duration = df_calls[['duration_val']].mean(skipna = True)
    print("df average response time {}".format(df_avg_response_time))
    print("df average duration {}".format(df_avg_duration))
    avg_response_time = df_avg_response_time["response_time_val"]
    avg_response_time = round(avg_response_time, 1)
    df_calls['avg_response_time'] = avg_response_time
    avg_duration = df_avg_duration["duration_val"]
    avg_duration = round(avg_duration, 0)
    print("average duration secs {}".format(avg_duration))
    df_calls['avg_duration'] = avg_duration
    avg_duration = format_mins_secs(avg_duration)
    print("average response time {}".format(avg_response_time))
    print("average duration {}".format(avg_duration))

    #df_location = get_location_df(host, db, replicaset, username, password)
    #print("got df_location")
    #print(df_location.columns.values)
    #df_calls = df_calls.join(df_location, on='room_number', lsuffix='_caller', rsuffix='_other')

    #df_calls = df_calls.filter(
    #    items=['orig_type', 'start_time', 'caller_ani', 'location_display', 'response_time', 'duration'])
    df_calls = df_calls.filter(
        items=['orig_type', 'start_time', 'caller_ani', 'name_calltaker', 'response_time', 'avg_response_time', 'duration', 'avg_duration'])
    df_calls['orig_type'] = df_calls['orig_type'].apply(format_orig_type)
    print("printing df_calls.columns")
    print(df_calls.columns.values)
    #df_calls.columns = ['Origination', 'Start Time', 'Caller', 'Location', 'Response Time', 'Duration']
    df_calls.columns = ['Origination', 'Start Time', 'Caller', 'Calltaker Name', 'Response Time', 'Avg Response Time', 'Duration', 'Avg Duration']
    df_calls.index.names = ['Call Id']

    return df_calls, avg_response_time, avg_duration


def get_abandoned_calls_report_pdf(host, db, replicaset, username, password):
    start_time_display, end_time_display = get_start_end_times_display()
    df = get_abandoned_calls_report_df(host, db, replicaset, username, password)
    # df = df.set_index('Origination')
    # df.columns = ['Start Time', 'Caller', 'Location']


    # df.style.set_properties(subset=['Location'], **{'width': '300px'})
    # df.style.set_properties(subset=['Start Time'], **{'width': '100px'})
    # df.style.set_properties(**{'font-size':'6pt'})

    template_vars = {"title": "Abandoned Calls from %s to %s" % (start_time_display, end_time_display),
                     "calls_pivot_table": df.to_html(index=False)}
    html_out = template.render(template_vars)
    from weasyprint import HTML
    HTML(string=html_out).write_pdf("abandoned-report.pdf")
    df.to_csv("abandoned-report.csv", sep='\t')


def get_completed_calls_report_pdf(host, db, replicaset, username, password):
    print("inside get_completed_calls_report_pdf")
    start_time_display, end_time_display = get_start_end_times_display()
    df, avg_response_time, avg_duration = get_completed_calls_report_df(host, db, replicaset, username, password)
    # df = df.set_index('Origination')
    # df.columns = ['Start Time', 'Caller', 'Location']


    # df.style.set_properties(subset=['Location'], **{'width': '300px'})
    # df.style.set_properties(subset=['Start Time'], **{'width': '100px'})
    # df.style.set_properties(**{'font-size':'6pt'})

    template_vars = {
        #"title": "Completed Calls from %s to %s" % (get_last_month_time_display(), get_now_time_display()),
        "title": "Completed Calls from %s to %s" % (start_time_display, end_time_display),
        "calls_pivot_table": df.to_html(index=False),
        "avg_response_time" : avg_response_time,
        "avg_duration" : avg_duration
    }
    html_out = template.render(template_vars)
    from weasyprint import HTML
    HTML(string=html_out).write_pdf("completed-report.pdf")
    df.to_csv("completed-report.csv", sep='\t')


if __name__ == '__main__':
    host = "mongodb:27017,mongodb-backup:27017,mongodb-arbiter:27017"
    db = "ng911"
    username = "pypsap"
    password = "ng911psap94109!"
    replicaset = "emergent911rs"
    get_completed_calls_report_pdf(host, db, replicaset, username, password)
    get_abandoned_calls_report_pdf(host, db, replicaset, username, password)

