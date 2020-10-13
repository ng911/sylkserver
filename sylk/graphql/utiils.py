
def update_params_with_args(params, args):
    relay_keys = ["first", "last", "before", "after"]
    for key, value in args.items():
        if key not in relay_keys:
            params[key] = value
    return params


def update_params_for_subscriptions(params, parent):
    if hasattr(parent, 'arguments'):
        arguments = parent.arguments
        for name, value in arguments.items():
            params[name] = value


