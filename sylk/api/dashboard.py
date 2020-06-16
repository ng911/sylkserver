import logging
import arrow
from datetime import datetime, timedelta
from flask import Blueprint, jsonify
from flask_cors import CORS
from flask_restful import reqparse

from .decorators import check_exceptions
from ..db.schema import ConferenceEvent, Conference
dashboard = Blueprint('dashboard', __name__,
                        template_folder='templates')

CORS(dashboard)

log = logging.getLogger('emergent-ng911')

def get_complex_time(dateval):
    return dateval.strftime("%Y,%m,%d,%H,%M,%S,%f")



@dashboard.route('/events', methods=['GET'])
@check_exceptions
def events():
    num_active_calls = Conference.objects(status__in=['ringing', 'ringing_queued', 'queued', 'active', 'on_hold']).count()
    start_time = datetime.utcnow() - timedelta(hours=1)
    #start_time_db = get_complex_time(start_time)
    num_abandoned_calls = Conference.objects(status='abandoned', start_time__gte = start_time).count()
    return {
        'num_abandoned_calls': num_abandoned_calls,
        'num_active_calls' : num_active_calls
    }

@dashboard.route('/active_events', methods=['GET'])
@check_exceptions
def active_events():
    '''
    active_line_chart = [
        {
            "$addFields": {
                "convertedDate": { "$dateFromString": {
                    "dateString": { "$substr": [ "$event_time", 0, 19 ] },
                    "format": "%Y,%m,%d,%H,%M,%S"
                } }
            }
        },
        {
            "$match": { "event": "active" }
        },
        {
            "$group" : {
                "_id" : {
                    "hour": { "$hour": "$convertedDate" }
                },
                "total" : { "$sum" : 1 }
            }
        },
        {
            "$sort": { "total": -1 }
        }
    ]
    '''
    current_dt = arrow.get()
    day_before = current_dt.shift(days=-1)
    pipeline = [
        {
            "$addFields": {
                "hour": {"$substr": ["$event_time", 11, 2]},
                "day": {"$substr": ["$event_time", 8, 2]},
                "month": {"$substr": ["$event_time", 5, 2]},
                "dateStr": {"$substr": ["$event_time", 5, 8]},
            }
        },
        {"$match": {"event": "active"}},
        {
            "$group": {
                "_id": "$dateStr",
                "total": {"$sum": 1}
            }
        },
        {"$sort": {"_id": 1}}
    ]
    events = list(ConferenceEvent.objects().filter(event_time__gte=day_before).aggregate(pipeline))
    data = []
    for r in arrow.Arrow.span_range('hour', day_before, current_dt):
        start = r[0]
        data.append({'time': start.isoformat(), 'total': 0})
    for event in events:
        event_dt = arrow.get(event['_id'], 'MM,DD,HH').replace(year=current_dt.year)
        for d in data:
            if d['time'] == event_dt.isoformat():
                d['total'] = event['total']
    return {'active_events': data}


@dashboard.route('/abandoned_events', methods=['GET'])
@check_exceptions
def abandoned_events():
    '''
    abandoned_line_chart = [
        {
            "$addFields": {
                "convertedDate": { "$dateFromString": {
                    "dateString": { "$substr": [ "$event_time", 0, 19 ] },
                    "format": "%Y,%m,%d,%H,%M,%S"
                } }
            }
        },
        {
            "$match": { "event": "abandoned" }
        },
        {
            "$group" : {
                "_id" : {
                    "hour": { "$hour": "$convertedDate" }
                },
                "total" : { "$sum" : 1 }
            }
        },
        {
            "$sort": { "total": -1 }
        }
    ]
    '''
    current_dt = arrow.get()
    day_before = current_dt.shift(days=-1)
    pipeline = [
        {
            "$addFields": {
                "hour": {"$substr": ["$event_time", 11, 2]},
                "day": {"$substr": ["$event_time", 8, 2]},
                "month": {"$substr": ["$event_time", 5, 2]},
                "dateStr": {"$substr": ["$event_time", 5, 8]},
            }
        },
        {"$match": {"event": "abandoned"}},
        {
            "$group": {
                "_id": "$dateStr",
                "total": {"$sum": 1}
            }
        },
        {"$sort": {"_id": 1}}
    ]
    events = list(ConferenceEvent.objects().filter(event_time__gte=day_before).aggregate(pipeline))
    data = []
    for r in arrow.Arrow.span_range('hour', day_before, current_dt):
        start = r[0]
        data.append({'time': start.isoformat(), 'total': 0})
    for event in events:
        event_dt = arrow.get(event['_id'], 'MM,DD,HH').replace(year=current_dt.year)
        for d in data:
            if d['time'] == event_dt.isoformat():
                d['total'] = event['total']
    return {'abandoned_events': data}

