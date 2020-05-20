from .schema import SpeedDial, SpeedDialGroup
from ..utils import get_json_from_db_obj


def get_speed_dial_groups(psap_id):
    groups = []
    for speedDialGroup in SpeedDialGroup.objects(psap_id=psap_id):
        groups.append(
            get_json_from_db_obj(speedDialGroup)
        )
    return groups


def get_speed_dials(psap_id, group_name=None):
    speedDials = []
    params = {
        "psap_id" : psap_id
    }
    if group_name != None and group_name != "":
        group = SpeedDialGroup.objects.get(group_name=group_name)
        params["group_id"] = group.id

    for speedDial in SpeedDial.objects(**params):
        speedDials.append(get_json_from_db_obj(speedDial, ignore_fields=['group']))

    return speedDials


def add_speed_dial_group(psap_id, group_name):
    # make sure the group does not exist first
    speedDialGroup = SpeedDialGroup()
    speedDialGroup.psap_id=psap_id
    speedDialGroup.group_name=group_name
    speedDialGroup.save()

    return get_json_from_db_obj(speedDialGroup)


def remove_speed_dial_group(group_id):
    speedDialGroup = SpeedDialGroup.objects.get(group_id=group_id)
    SpeedDial.objects(group_id=group_id).delete()
    speedDialGroup.delete()


def edit_speed_dial_group(group_id, group_name):
    speedDialGroup = SpeedDialGroup.objects.get(group_id=group_id)
    speedDialGroup.group_name = group_name
    speedDialGroup.save()


def add_speed_dial(psap_id, dest, name, group_id=None):
    speedDial = SpeedDial()
    if group_id != None:
        speedDial.group_id = group_id
        speedDial.group = SpeedDialGroup.objects.get(group_id=group_id)
    speedDial.name = name
    speedDial.psap_id = psap_id
    speedDial.dest = dest
    speedDial.save()
    return get_json_from_db_obj(speedDial, ignore_fields=['group'])


def remove_speed_dial(speed_dial_id):
    SpeedDial.objects.get(speed_dial_id=speed_dial_id).delete()


def get_speed_dial(speed_dial_id):
    return get_json_from_db_obj(
        SpeedDial.objects.get(speed_dial_id=speed_dial_id), ignore_fields=['group']
    )


def edit_speed_dial(speed_dial_id, payload):
    speedDial = SpeedDial.objects.get(speed_dial_id=speed_dial_id)
    if payload["dest"] != None:
        speedDial.dest = payload["dest"]
    if payload["name"] != None:
        speedDial.name = payload["name"]
    speedDial.save()

