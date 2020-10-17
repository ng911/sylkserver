from .schema import Psap
from .aws import add_dns_a_record, add_dns_cname_record

def get_psap_from_domain(domain_name):
    psapObj = Psap.objects.get(domain=domain_name)
    return str(psapObj.psap_id)

def get_calltaker_server(domain_name):
    sip_reg_domain = f"reg.{domain_name}"
    return sip_reg_domain

def get_psap_name(psap_id):
    psapObj = Psap.objects.get(psap_id=psap_id)
    psap_name = psapObj.name
    return psap_name


def get_overflow_uri(psap_id):
    # todo - add max calls in queue, assume 0 for now
    psapObj = Psap.objects.get(psap_id=psap_id)
    psap_name = psapObj.name
    if hasattr(psapObj, 'enable_overflow_handling') and (psapObj.enable_overflow_handling) and \
       hasattr(psapObj, 'overflow_uri') and (psapObj.overflow_uri != ""):
        return psapObj.overflow_uri, psap_name
    return None, psap_name


def create_psap_domains(domain_name, base_domain="emergentpsap.com", aws_region="us-west-2"):
    '''
    create domain names for
        kamailio proxy, kamailio registration, admin site, website
    :param domain_name:
    :param base_domain:
    :param aws_region:
    :return:
    '''
    admin_domain = f"admin.{domain_name}"
    sip_reg_domain = f"reg.{domain_name}"
    sip_proxy_domain = f"proxy.{domain_name}"
    website_domain = domain_name
    base_reg_domain = f"ws.registration.kamailio.{aws_region}.{base_domain}"
    base_proxy_domain = f"proxy.kamailio.az1.{aws_region}.{base_domain}"
    base_website_domain = f"web.{aws_region}.{base_domain}"

    # create admin site
    add_dns_cname_record(admin_domain, base_domain, base_website_domain)
    add_dns_cname_record(website_domain, base_domain, base_website_domain)
    add_dns_cname_record(sip_reg_domain, base_domain, base_reg_domain)
    add_dns_cname_record(sip_proxy_domain, base_domain, base_proxy_domain)


def create_psap(name, domain_name, base_domain="emergentpsap.com", aws_region="us-west-2"):
    from .schema_sqlalchemy import add_psap_domain
    from .schema import Psap
    sip_reg_domain = f"reg.{domain_name}"
    sip_proxy_domain = f"proxy.{domain_name}"
    add_psap_domain(sip_proxy_domain)
    add_psap_domain(sip_reg_domain)
    create_psap_domains(domain_name, base_domain, aws_region)
    psapObj = Psap(name=name, domain=domain_name)
    psapObj.save()
    return psapObj

