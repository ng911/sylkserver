import logging
from .schema import Queue, QueueMember
from ..utils import get_json_from_db_obj

log = logging.getLogger('emergent-ng911')

def get_queues(psap_id):
    queues = []
    for queue in Queue.objects(psap_id=psap_id):
        queues.append(
            get_json_from_db_obj(queue)
        )
    return queues


def get_queue_details(queue_id):
    return get_json_from_db_obj(Queue.objects.get(queue_id=queue_id))


def get_queue_members(queue_id):
    queueMembers = []
    for queueMember in QueueMember.objects(queue_id=queue_id):
        queueMembers.append(
            get_json_from_db_obj(queueMember)
        )
    return queueMembers


def add_queue(psap_id, queue_name, user_ids=[]):
    log.info("add_queue psap_id %r, queue_name %r, user_ids %r", psap_id, queue_name, user_ids)
    queue = Queue()
    queue.name = queue_name
    queue.psap_id = psap_id
    queue.save()
    queue_id = str(queue.queue_id)
    if user_ids != None:
        for user_id in user_ids:
            log.info("add_queue adding user_id %r, queue_id %r", user_id, queue_id)
            add_calltaker_to_queue(user_id, queue_id)
    return {
        "queue_id" : queue_id
    }


def edit_queue(queue_id, queue_name, user_ids=None):
    queue = Queue.objects.get(queue_id=queue_id)
    queue.name = queue_name
    queue.save()
    if user_ids != None:
        delete_user_ids = []
        add_user_ids = user_ids
        for memberObj in QueueMember.objects(queue_id=queue_id):
            user_id = str(memberObj.user_id)
            if user_id in add_user_ids:
                add_user_ids.remove(user_id)
            else:
                delete_user_ids.append(user_id)
            for user_id in add_user_ids:
                log.info("add_queue adding user_id %r, queue_id %r", user_id, queue_id)
                add_calltaker_to_queue(user_id, queue_id)
            for user_id in add_user_ids:
                log.info("remove_calltaker_from_queue user_id %r, queue_id %r", user_id, queue_id)
                remove_calltaker_from_queue(user_id, queue_id)


def remove_queue(queue_id):
    QueueMember.objects(queue_id=queue_id).delete()
    Queue.objects.get(queue_id=queue_id).delete()


def add_calltaker_to_queue(user_id, queue_id):
    # make sure queue exists
    Queue.objects.get(queue_id=queue_id)
    queueMember = QueueMember()
    queueMember.queue_id = queue_id
    queueMember.user_id = user_id
    queueMember.save()


def remove_calltaker_from_queue(user_id, queue_id):
    QueueMember.objects.get(queue_id=queue_id, user_id=user_id).delete()


