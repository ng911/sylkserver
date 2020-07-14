
from sylk.db.schema import User
from sylk.data.calltaker import CalltakerData
from sylk.applications import ApplicationLogger

log = ApplicationLogger(__package__)

def get_calltakers(acd_strategy, user_ids):
    if acd_strategy == 'ring_all':
        # for now we return all queue_members
        log.info("get_calltakers user_ids %r", user_ids)
        calltaker_data = CalltakerData()
        available_calltakers = calltaker_data.available_calltakers
        available_calltakers = {user_id:user for user_id, user in available_calltakers.iteritems() if user_id in user_ids}
        log.info("get_calltakers available_calltakers %r", available_calltakers)
        return available_calltakers
    elif acd_strategy == 'random':
        raise NotImplementedError
    elif acd_strategy == 'most_idle':
        raise NotImplementedError
    elif acd_strategy == 'round_robin':
        raise NotImplementedError
    raise NotImplementedError

