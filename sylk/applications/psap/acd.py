
from sylk.db.schema import User

def get_calltakers(queue_details, queue_members):
    if queue_details.acd_strategy == 'ring_all':
        # for now we return all queue_members
        user_ids = [queue_member.user_id for queue_member in queue_members]
    elif queue_details.acd_strategy == 'random':
        raise NotImplementedError
    elif queue_details.acd_strategy == 'most_idle':
        raise NotImplementedError
    elif queue_details.acd_strategy == 'round_robin':
        raise NotImplementedError
    users = []
    for user_id in user_ids:
        user_obj = User.objects.get(user_id=user_id)
        users.append(user_obj.username)

    return users

