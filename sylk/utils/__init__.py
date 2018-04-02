import bson

def dump_var(log, data):
    if isinstance(data, object):
        dump_object_member_vars(log, data)
        dump_object_member_funcs(log, data)
    else:
        log.info(u'    %r' % data)


def dump_object_member_vars(log, obj):
    log.info(u'member vars ')
    #for key in obj.__dict__.keys():
    #    log.info(u'    %r' % key)
    for key in [method_name for method_name in dir(obj) if not callable(getattr(obj, method_name))]:
        log.info(u'    %r' % key)


def dump_object_member_funcs(log, obj):
    log.info(u'member funcs ')
    for key in [method_name for method_name in dir(obj) if callable(getattr(obj, method_name))]:
        log.info(u'    %r' % key)

'''
 only one of ignore_fields or use_fields should be specified.
 give an array of fields to be ignored or added
'''
def get_json_from_db_obj(db_obj, ignore_fields=None, include_fields=None):
    db_obj_dict = db_obj.to_mongo(True).to_dict()
    if include_fields is None:
        all_fields = db_obj_dict.keys()
        if ignore_fields is None:
            ignore_fields = ['_id']
        else:
            if '_id' not in ignore_fields:
                ignore_fields.append('_id')
        include_fields = list(set(all_fields)-set(ignore_fields))
    json_data = {x:str(db_obj_dict[x]) if isinstance(db_obj_dict[x],  bson.objectid.ObjectId) else db_obj_dict[x] for x in include_fields}
    return json_data



