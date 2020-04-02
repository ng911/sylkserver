from schema import Queue, QueueMember


def get_queue_details(queue_id):
    return Queue.objects.get(queue_id=queue_id)


def get_queue_members(queue_id):
    return QueueMember.objects(queue_id=queue_id)


