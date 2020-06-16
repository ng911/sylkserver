from flask import jsonify
import mongoengine
from traceback import format_exc
import functools

try:
    from sylk.applications import ApplicationLogger
    log = ApplicationLogger(__package__)
except:
    import logging
    log = logging.getLogger("emergent-ng911")


def check_exceptions(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            status_code = 200
            json_response = func(*args, **kwargs)
            if json_response is None:
                json_response = {}
            #log.info("json_response is %r", json_response)
        except mongoengine.ValidationError as e:
            stacktrace = format_exc()
            log.error(stacktrace)
            log.error(str(e))
            status_code = 500
            json_response = {
                "error_code" : "db_validation_error",
                "reason" : str(e)
            }
        except mongoengine.MultipleObjectsReturned as e:
            stacktrace = format_exc()
            log.error(stacktrace)
            log.error(str(e))
            status_code = 500
            json_response = {
                "error_code" : "db_multiple_objects",
                "reason" : str(e)
            }
        except mongoengine.DoesNotExist as e:
            stacktrace = format_exc()
            log.error(stacktrace)
            log.error(str(e))
            status_code = 500
            json_response = {
                "error_code" : "db_does_not_exist",
                "reason" : str(e)
            }
        except mongoengine.NotUniqueError as e:
            log.info("got exception NotUniqueError %r", e)
            status_code = 500
            json_response = {
                "error_code": "db_not_unique",
                "reason": str(e)
            }
            log.info("check_exceptions except")
            log.info("except json_response is %r", json_response)
            log.info("except status_code is %r", status_code)
        except ValueError as e:
            stacktrace = format_exc()
            log.error(stacktrace)
            log.error(str(e))
            status_code = 500
            json_response = {
                "error_code" : "invalid_value",
                "reason" : str(e)
            }
        except Exception as e:
            stacktrace = format_exc()
            log.error(stacktrace)
            log.error(str(e))
            status_code = 500
            json_response = {
                "error_code" : "general_errpr",
                "reason" : str(e)
            }
        except:
            stacktrace = format_exc()
            log.error(stacktrace)
            status_code = 500
            json_response = {
                "error_code": "general_errpr",
            }
        finally:
            log.info("check_exceptions in finally")
            #log.info("check_exceptions finally json_response is %r, status_code is %r", json_response, status_code)
            return json_response, status_code

    return wrapper

