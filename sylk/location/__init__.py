import datetime
import traceback
from twisted.internet import reactor

from .aliquery import send_ali_request, check_ali_format_supported
from ..db.schema import Location, Conference, ConferenceParticipant, User
from ..wamp import publish_update_call, publish_update_location_success, publish_update_location_failed
from ..db.calls import get_conference_json
from .alidump import dump_ali

try:
    from sylk.applications import ApplicationLogger
    log = ApplicationLogger(__package__)
except:
    import logging
    log = logging.getLogger('emergent-ng911')


def get_location_display(ali_result):
    location_display = ''
    if ('location' in ali_result) and (ali_result['location'] != ''):
        location_display = ali_result['location']
    if ('community' in ali_result) and (ali_result['community'] != ''):
        if location_display == '':
            location_display = ali_result['community']
        else:
            location_display = "%s, %s" % (location_display, ali_result['community'])

    if ('state' in ali_result) and (ali_result['state'] != ''):
        if location_display == '':
            location_display = ali_result['state']
        else:
            location_display = "%s, %s" % (location_display, ali_result['state'])

    return location_display


def get_initialized_ali_data():
    ali_data = {}
    ali_data['postal'] = ""
    ali_data['community'] = ""
    ali_data['state'] = ""
    ali_data['name'] = ""
    ali_data['latitude'] = ""
    ali_data['longitude'] = ""
    ali_data['radius'] = ""
    ali_data['service_provider'] = ""
    ali_data['class_of_service'] = ""
    ali_data['agencies_display'] = ""

    return ali_data


def process_ali_success(result):
    log.info("process_ali_success for %r", result)
    if result is  None:
        log.error("process_ali_success error result is %r", result)
        return
    (room_number, number, ali_format, ali_result, ali_result_xml, raw_ali_data) = result
    log.info("aliResult %r, aliResultXml %r, rawAliData %r", ali_result, ali_result_xml, raw_ali_data)
    # store the ali result in database and send a updated message
    if len(ali_result) == 0:
        conference_db_obj = Conference.objects.get(room_number=room_number)
        conference_db_obj.ali_result = "no records found"
        conference_db_obj.save()
        return

    try:
        location_db_obj = Location()
        location_db_obj.room_number = room_number
        location_db_obj.ali_format = ali_format
        location_db_obj.raw_format = raw_ali_data
        location_db_obj.state = ali_result['state']
        location_db_obj.name = ali_result['name']
        location_db_obj.phone_number = ali_result['phone_number']
        location_db_obj.callback = ali_result['callback']
        location_db_obj.service_provider = ali_result['service_provider']
        location_db_obj.class_of_service = ali_result['class_of_service']
        location_db_obj.community = ali_result['community']

        location_db_obj.latitude = float(ali_result['latitude'])
        location_db_obj.longitude = float(ali_result['longitude'])
        location_db_obj.radius = float(ali_result['radius'])
        location_db_obj.location = ali_result['location']

        location_db_obj.otcfield = ali_result['otcfield']
        location_db_obj.psap_no = ali_result['psap_no']
        location_db_obj.esn = ali_result['esn']
        location_db_obj.postal = ali_result['postal']
        location_db_obj.psap_name = ali_result['psap_name']
        location_db_obj.pilot_no = ali_result['pilot_no']

        location_db_obj.agencies_display = ali_result['agencies_display']
        location_db_obj.fire_no = ali_result['fire_no']
        location_db_obj.ems_no = ali_result['ems_no']
        location_db_obj.police_no = ali_result['police_no']
        location_db_obj.time = location_db_obj.updated_at = datetime.datetime.utcnow()

        location_db_obj.save()

        # in case lat and long values are wrong we can safely ignore it
        # this is causing problems not needed
        #log.info("location object created with id %r", str(location_db_obj.location_id))
        #if (ali_result['latitude'] != '') and (ali_result['longitude'] != ''):
        #    location_db_obj.location_point = [float(ali_result['longitude']), float(ali_result['latitude'])]
        #location_db_obj.save()

        # update call location in Conference table as well
        location_display = get_location_display(ali_result)
        conference_db_obj = Conference.objects.get(room_number=room_number)
        conference_db_obj.location_display = location_display
        conference_db_obj.callback_number = location_db_obj.callback
        conference_db_obj.ali_result = "success"
        conference_db_obj.save()

        if conference_db_obj.status in ['init', 'ringing', 'ringing_queued', 'queued', 'active']:
            dump_ali(room_number, raw_ali_data)

        call_data = get_conference_json(conference_db_obj)
        publish_update_call(room_number, call_data)
        publish_update_location_success(room_number, ali_result, location_display)
    except Exception as e:
        stacktrace = traceback.format_exc()
        log.error("error in process_ali_success %r",e)
        log.error(stacktrace)


def dump_ali(room_number, ali_data=None, calltaker=None):
    # get active calltakers and station ids
    log.info("dump_ali for room %s", room_number)
    if ali_data is None:
        # get latest ali data from location db
        try:
            location_db_obj = Location.objects(room_number=room_number).order_by('-updated_at').first()
            if (location_db_obj is None) or not hasattr(location_db_obj, 'raw_format'):
                return
            ali_data = location_db_obj.raw_format
        except:
            return
    if (calltaker is None) or (calltaker == ''):
        station_ids = []
        for conference_participant_obj in ConferenceParticipant.objects(room_number=room_number, is_active=True,
                                                                            is_calltaker=True):
            calltaker = conference_participant_obj.name
            try:
                calltaker_db_obj = User.objects.get(username=calltaker)
                if hasattr(calltaker_db_obj, 'station_id') and (calltaker_db_obj.station_id != ''):
                    station_ids.append(calltaker_db_obj.station_id)
            except Exception as e:
                stacktrace = traceback.format_exc()
                log.error("%s", stacktrace)
                log.error("error in getting calltaker data %s", e)
        for station_id in station_ids:
            log.info("send ali data to station_id  %s", station_id)
            dump_ali(station_id, ali_data)
    else:
        try:
            calltaker_db_obj = User.objects.get(username=calltaker)
            if hasattr(calltaker_db_obj, 'station_id') and (calltaker_db_obj.station_id != ''):
                dump_ali(calltaker_db_obj.station_id, ali_data)
        except Exception as e:
            stacktrace = traceback.format_exc()
            log.error("%s", stacktrace)
            log.error("error in getting calltaker data %s", e)


def ali_lookup(room_number, number, ali_format, station_id=''):
    log.info("inside ali_lookup for room %r, number %r, format %r", room_number, number, ali_format)

    ali_available = check_ali_format_supported(ali_format)
    log.info("inside ali_lookup ali_available %r", ali_available)
    if not ali_available:
        return

    # setup ali status to pending
    try:
        conf_db_obj = Conference.objects.get(room_number=room_number)
        if ali_available:
            conf_db_obj.ali_result = 'pending'
        else:
            conf_db_obj.ali_result = 'none'
        conf_db_obj.save()

        call_data = get_conference_json(conf_db_obj)
        publish_update_call(room_number, call_data)
    except:
        # if the room does not exist we ignore this
        pass

    # to do add psap location update wamp

    d, request_id = send_ali_request(room_number, number, ali_format)

    def process_ali_failed(failure):
        log.info("ali_failed number %r, %r", room_number, number)
        try:
            conference_db_obj = Conference.objects.get(room_number=room_number)
            conference_db_obj.ali_result = "failed"
            conference_db_obj.save()
            call_data = get_conference_json(conference_db_obj)
            publish_update_call(room_number, call_data)
        except Exception as e:
            stacktrace = traceback.format_exc()
            log.error('%s', stacktrace)
            log.error('process_ali_failed %s', str(e))
        publish_update_location_failed(room_number)

    if d is not None:
        d.addErrback(process_ali_failed)
        d.addCallback(process_ali_success)
    else:
        process_ali_failed("format {} not available)".format(ali_format))

    return request_id

'''
def aliRebid(self):
    log.debug("inside aliRebid")
    if self.rebidPending:
        return
    self.rebidPending = True
    self.data.rebidStatus = "Trying .."
    alilink1 = self.ali_ip1
    alilink2 = self.ali_ip2
    ali_port = self.ali_port
    ali_format = self.ali_format

    if ((alilink1 and (alilink1 != '')) or (alilink2 and (alilink2 != ''))) and (ali_port > 0):
        self.data.rebidStatus = "pending.."

        # aliNumber = self.caller.name
        aliNumber = self.aliNumber
        logger.debug('aliNumber is %r, alilink1 is %r', aliNumber, alilink1)
        (aliResult, aliResultCivicXML, rawAliData) = doAliQuery(aliNumber, alilink1, alilink2, ali_port, ali_format)
        logger.debug("aliResult %r, aliResultXml %r, rawAliData %r", aliResult, aliResultCivicXML, rawAliData)

        self.rawAliData = rawAliData
        self.data.rebidStatus = "Done"
        if aliResult and (len(aliResult) > 0):
            self.sendAliData()
            # if rebid is successfull we populate the results in the relevant field
            self.location.append(aliResultCivicXML)
            self.data.caller.location = aliResult['postal']
            self.data.caller.community = aliResult['community']
            self.data.caller.state = aliResult['state']
            self.data.caller.provider = aliResult['service_provider']
            self.data.caller.cls = aliResult['class_of_service']
            self.data.caller.latitude = aliResult['latitude']
            self.data.caller.longitude = aliResult['longitude']
            self.data.caller.radius = aliResult['radius']
            self.data.caller.agenciesDisplay = aliResult['agencies_display']
            if aliResult['callback'] == "":
                self.data.caller.callback = aliNumber
            else:
                self.data.caller.callback = aliResult['callback']
            self.data.caller.pAni = aliNumber
            self.data.caller.name = aliResult['name']

            self.data.ali_agencies = bindable.List();
            if len(aliResult['fire_no']) > 0:
                self.data.ali_agencies.append(bindable.Object(
                    {'displayName': 'Fire - ' + aliResult['fire_no'], 'phoneNumber': aliResult['fire_no']}))

            if len(aliResult['ems_no']) > 0:
                self.data.ali_agencies.append(bindable.Object(
                    {'displayName': 'EMS - ' + aliResult['ems_no'], 'phoneNumber': aliResult['ems_no']}))

            if len(aliResult['police_no']) > 0:
                self.data.ali_agencies.append(bindable.Object(
                    {'displayName': 'Police - ' + aliResult['police_no'], 'phoneNumber': aliResult['police_no']}))
            self.data.locations.insert(
                bindable.Object(location=self.data.caller.location, community=self.data.caller.community,
                                state=self.data.caller.state, name=self.data.caller.name, \
                                latitude=self.data.caller.latitude, longitude=self.data.caller.longitude,
                                radius=self.data.caller.radius))
            logger.debug("self.data.locations length is %r", len(self.data.locations))
            # caller = bindable.Object(callId=request.callId, category=request.callerCategory, location=postal, community=community, state=state, \
            #                                        contact=str(request.caller), contactDisplay=self.getContactDisplay(request.caller), callback=request.contact and str(request.contact), alternate=None, \
            #                                        name=callerName, provider=serviceProvider, cls=classOfService, secondary='', latitude=latitude, longitude=longitude, radius=radius)

    else:
        self.data.rebidStatus = "No ALI Link"

    self.rebidPending = False
'''

def runTests():
    from aliquery import init_ali_links
    log.info("start running tests")
    ali_links = [("127.0.0.1", 11010, "30WWireless"), ("159.65.73.31", 11010, "30WWireless"), ]
    init_ali_links(ali_links)
    #send_ali_request(room_number='1100', number='4153055512', ali_format="30WWireless")
    reactor.callLater(5, ali_lookup, '5ba81b2b1e32497e9bd9e38c2ee9cfcf', '4153054541', "30WWireless")
    reactor.run()

if __name__ == '__main__':  # parse command line options, and set the high level properties
    log.info("starting location tests")
    reactor.callLater(0, runTests)
    log.info("starting reactor.run")
    reactor.run()
    log.info("all done")


