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
    active_line_chart = [
        {
            "$addFields": {
                "year": {"$substr": ["$event_time", 0, 4]},
                "month": {"$substr": ["$event_time", 5, 2]},
                "day": {"$substr": ["$event_time", 8, 2]},
                "hour": {"$substr": ["$event_time", 11, 2]},
                "minute": {"$substr": ["$event_time", 14, 2]},
                "second": {"$substr": ["$event_time", 17, 2]}
            }
        },
        {
            "$match": {"event": "active"}
        },
        {
            "$group": {
                "_id": "$hour",
                "total": {"$sum": 1}
            }
        },
        {
            "$sort": {"_id": 1 }
        }
    ]
    active_events = ConferenceEvent.objects().aggregate(active_line_chart)
    return {
        'active_events': list(active_events),
    }

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
    pipeline = [
        {
            "$addFields": {
                "year": {"$substr": ["$event_time", 0, 4]},
                "month": {"$substr": ["$event_time", 5, 2]},
                "day": {"$substr": ["$event_time", 8, 2]},
                "hour": {"$substr": ["$event_time", 11, 2]},
                "minute": {"$substr": ["$event_time", 14, 2]},
                "second": {"$substr": ["$event_time", 17, 2]}
            }
        },
        {
            "$match": {
                "event": "abandoned",
                "year": current_dt.format('YYYY'),
                "month": current_dt.format('MM'),
                "day": current_dt.format('DD')
            }
        },
        {
            "$group": {
                "_id": "$hour",
                "total": {"$sum": 1}
            }
        },
        {
            "$sort": {"_id": 1}
        }
    ]
    events = ConferenceEvent.objects().aggregate(pipeline)
    return {'abandoned_events': list(events)}

