from .schema import Psap

def get_psap_from_domain(domain_name):
    psapObj = Psap.objects.get(domain=domain_name)
    return str(psapObj.psap_id)

def get_psap_name(psap_id):
    psapObj = Psap.objects.get(psap_id=psap_id)
    psap_name = psapObj.name
    return psap_name

def get_overflow_uri(psap_id):
    # todo - add max calls in queue, assume 0 for now
    psapObj = Psap.objects.get(psap_id=psap_id)
    psap_name = psapObj.name
    if hasattr(psapObj.enable_overflow_handling) and (psapObj.enable_overflow_handling) and \
       hasattr(psapObj.overflow_uri) and (psapObj.overflow_uri != ""):
        return psapObj.overflow_uri, psap_name
    return None, psap_name
