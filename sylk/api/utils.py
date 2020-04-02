from flask import request, url_for
from urlparse import urlparse, urljoin

def get_argument(arg_name, default=None):
    if (request.content_type is not None) and request.content_type.startswith('application/json'):
        request_data = request.get_json()
        if arg_name in request_data:
            return request_data[arg_name]
        else:
            return default
    else:
        if arg_name in request.values:
            return request.values[arg_name]
        return default


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc


def redirect_url():
    return request.args.get('next') or \
           request.referrer or \
           url_for('index')

