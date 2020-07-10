from .schema import Psap

def get_psap_from_domain(domain_name):
    psapObj = Psap.objects.get(domain=domain_name)
    return str(psapObj.psap_id)


