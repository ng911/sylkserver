

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


