import logging
import json
import boto3
try:
    from sylk.applications import ApplicationLogger
    log = ApplicationLogger(__package__)
except:
    import logging
    log = logging.getLogger('emergent-ng911')

from ..config import AWS_ACCESS_KEY, AWS_SECRET_KEY

client = boto3.client('route53', aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY)

def get_hosted_zone_id(zone_name):
    json_response = client.list_hosted_zones()
    hosted_zones = json_response["HostedZones"]
    for zone in hosted_zones:
        name = zone["Name"]
        if name == zone_name:
            zone_id = zone["Id"]
            return zone_id
    return None


def add_dns_a_record(sub_domain, domain, ip_address):
    log.info("add dns cname for sub_domain %r, domain %r, value %r", sub_domain, domain, ip_address)
    zone_id = get_hosted_zone_id(domain)
    if zone_id == None:
        log.error("domain does not exist in Route 53")
        return False

    response = client.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch={
            'Comment': 'string',
            'Changes': [
                {
                    'Action': 'CREATE',
                    'ResourceRecordSet': {
                        'Name': sub_domain,
                        'Type': 'A',
                        'TTL': 300,
                        'ResourceRecords': [
                            {
                                'Value': ip_address
                            },
                        ]
                    }
                },
            ]
        }
    )

    resp_meta_data = response["ResponseMetadata"]
    log.debug(response)
    return resp_meta_data["HTTPStatusCode"] == 200


def add_dns_cname_record(sub_domain, domain, value):
    log.info("add dns cname for sub_domain %r, domain %r, value %r", sub_domain, domain, value)
    zone_id = get_hosted_zone_id(domain)
    if zone_id == None:
        log.error("domain does not exist in Route 53")
        return False

    response = client.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch={
            'Comment': 'string',
            'Changes': [
                {
                    'Action': 'CREATE',
                    'ResourceRecordSet': {
                        'Name': sub_domain,
                        'Type': 'CNAME',
                        'TTL': 300,
                        'ResourceRecords': [
                            {
                                'Value': value
                            },
                        ]
                    }
                },
            ]
        }
    )

    resp_meta_data = response["ResponseMetadata"]
    log.debug(response)
    return resp_meta_data["HTTPStatusCode"] == 200



