import logging
from flask import Blueprint, jsonify
from flask_cors import CORS
from flask_restful import reqparse

from .decorators import check_exceptions
from ..db.schema import ConferenceEvent
dashboard = Blueprint('dashboard', __name__,
                        template_folder='templates')

CORS(dashboard)

log = logging.getLogger('emergent-ng911')


@dashboard.route('/events', methods=['GET'])
@check_exceptions
def events():
    bar_chart_pipeline = [
        {
            "$lookup": {
                "from": "conference",
                "localField": "room_number",
                "foreignField": "room_number",
                "as": "conference_items"
            }
        },
        {
            "$group" : {
                "_id" : "$event",
                "total" : { "$sum" : 1 }
            }
        },
        {
            "$sort": { "total": -1 }
        }
    ]
    events = ConferenceEvent.objects().aggregate(bar_chart_pipeline)
    return {
        'events': list(events),
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
            "$sort": {"total": -1}
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
    abandoned_line_chart = [
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
            "$match": {"event": "abandoned"}
        },
        {
            "$group": {
                "_id": "$hour",
                "total": {"$sum": 1}
            }
        },
        {
            "$sort": {"total": -1}
        }
    ]
    abandoned_events = ConferenceEvent.objects().aggregate(abandoned_line_chart)
    return {
        'abandoned_events': list(abandoned_events)
    }

