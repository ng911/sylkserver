import logging
from .schema import Psap
from .aws import add_dns_a_record, add_dns_cname_record
from ..config import PSAP_BASE_DOMAIN

log = logging.getLogger('emergent-ng911')


def get_psap_from_domain(domain_name):
    psapObj = Psap.objects.get(domain=domain_name)
    return str(psapObj.psap_id)


def get_psap_from_website_domain(domain_name):
    log.info('inside get_psap_from_website_domain for %r', domain_name)
    admin_base_domain = ".admin.%s" % PSAP_BASE_DOMAIN.rstrip('.')
    calltaker_base_domain = ".calltaker.%s" % PSAP_BASE_DOMAIN.rstrip('.')
    domain_name_prefix = None
    if domain_name.endswith(admin_base_domain):
        domain_name_prefix = domain_name[:len(domain_name)-len(admin_base_domain)]
    elif domain_name.endswith(calltaker_base_domain):
        domain_name_prefix = domain_name[:len(domain_name)-len(calltaker_base_domain)]
    log.info('inside get_psap_from_website_domain domain_name_prefix %r', domain_name_prefix)
    if domain_name_prefix != None:
        try:
            psapObj = Psap.objects.get(domain_name_prefix=domain_name_prefix)
            log.info('inside get_psap_from_website_domain psap_id %r', str(psapObj.psap_id))
            return str(psapObj.psap_id)
        except:
            pass
    return None


def get_psap_from_domain_prefix(domain_prefix):
    psapObj = Psap.objects.get(domain=domain_prefix)
    return str(psapObj.psap_id)

def get_proxy_domain_suffix():
    return "proxy.%s" % PSAP_BASE_DOMAIN

def get_domain_prefix_from_proxy_domain(proxy_domain):
    proxy_domain_suffix = get_proxy_domain_suffix()
    if proxy_domain.endswith(proxy_domain_suffix):
        domain_prefix = proxy_domain[:len(proxy_domain) - len(proxy_domain_suffix) - 1]
        return domain_prefix
    return None

def get_calltaker_reg_server(domain_name_prefix):
    sip_reg_domain = "%s.reg.%s" % (domain_name_prefix, PSAP_BASE_DOMAIN)
    return sip_reg_domain

def get_psap_name(psap_id):
    psapObj = Psap.objects.get(psap_id=psap_id)
    psap_name = psapObj.name
    return psap_name

def get_psap_domain(psap_id):
    psapObj = Psap.objects.get(psap_id=psap_id)
    psap_domain = psapObj.domain
    return psap_domain

def get_psap_domain_prefix(psap_id):
    psapObj = Psap.objects.get(psap_id=psap_id)
    domain_name_prefix = psapObj.domain_name_prefix
    return domain_name_prefix

def get_overflow_uri(psap_id):
    # todo - add max calls in queue, assume 0 for now
    psapObj = Psap.objects.get(psap_id=psap_id)
    psap_name = psapObj.name
    if hasattr(psapObj, 'enable_overflow_handling') and (psapObj.enable_overflow_handling) and \
       hasattr(psapObj, 'overflow_uri') and (psapObj.overflow_uri != ""):
        return psapObj.overflow_uri, psap_name
    return None, psap_name


def create_psap_domains_dns(domain_name_prefix):
    '''
    create domain names for
        kamailio proxy, kamailio registration, admin site, website
    :param domain_name:
    :param base_domain:
    :param aws_region:
    :return:
    '''
    base_website_domain = "calltaker.%s" % PSAP_BASE_DOMAIN
    base_admin_domain = "admin.%s" % PSAP_BASE_DOMAIN
    base_reg_domain = "reg.%s" % PSAP_BASE_DOMAIN
    base_proxy_domain = "proxy.%s" % PSAP_BASE_DOMAIN

    website_domain = "%s.%s" % (domain_name_prefix, base_website_domain)
    admin_domain = "%s.%s" % (domain_name_prefix, base_admin_domain)
    sip_reg_domain = "%s.%s" % (domain_name_prefix, base_reg_domain)
    sip_proxy_domain = "%s.%s" % (domain_name_prefix, base_proxy_domain)

    '''
    base_reg_domain = "ws.registration.kamailio.%s.%s" % (aws_region, base_domain)
    base_proxy_domain = "proxy.kamailio.az1.%s.%s" % (aws_region, base_domain)
    base_website_domain = "web.%s.%s" % (aws_region, base_domain)
    '''

    # create admin site
    add_dns_cname_record(admin_domain, PSAP_BASE_DOMAIN, base_admin_domain)
    add_dns_cname_record(website_domain, PSAP_BASE_DOMAIN, base_website_domain)
    add_dns_cname_record(sip_reg_domain, PSAP_BASE_DOMAIN, base_reg_domain)
    add_dns_cname_record(sip_proxy_domain, PSAP_BASE_DOMAIN, base_proxy_domain)

def create_psap(name, domain_name_prefix):
    from .schema_sqlalchemy import add_kamailio_domain
    from .schema import Psap
    from ..config import USE_KAMAILIO, USE_AWS_ROUTE_53

    sip_reg_domain = "%s.reg.%s" % (domain_name_prefix, PSAP_BASE_DOMAIN)
    sip_proxy_domain = "%s.proxy.%s" % (domain_name_prefix, PSAP_BASE_DOMAIN)

    if USE_KAMAILIO:
        add_kamailio_domain(sip_proxy_domain)
        add_kamailio_domain(sip_reg_domain)

    if USE_AWS_ROUTE_53:
        create_psap_domains_dns(domain_name_prefix)

    psapObj = Psap(name=name, domain_name_prefix=domain_name_prefix)
    psapObj.domain = sip_proxy_domain
    psapObj.save()
    return psapObj

