from sylk.applications import ApplicationLogger
from aliquery import send_ali_request
from sylk.db.schema import Location
from sylk.wamp import publish_update_location_success, publish_update_location_failed
import traceback

log = ApplicationLogger(__package__)

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
    (room_number, number, ali_format, ali_result, ali_result_xml, raw_ali_data) = result
    log.debug("aliResult %r, aliResultXml %r, rawAliData %r", ali_result, ali_result_xml, raw_ali_data)
    # store the ali result in database and send a updated message
    try:
        location_db_obj = Location()
        location_db_obj.room_number = room_number
        location_db_obj.ali_format = ali_format
        location_db_obj.raw_format = raw_ali_data
        location_db_obj.state = ali_result.state
        location_db_obj.name = ali_result.name
        location_db_obj.phone_number = ali_result.phone_number
        location_db_obj.callback = ali_result.callback
        location_db_obj.service_provider = ali_result.service_provider
        location_db_obj.class_of_service = ali_result.class_of_service
        location_db_obj.community = ali_result.community

        location_db_obj.latitiude = float(ali_result.latitiude)
        location_db_obj.longitude = float(ali_result.longitude)
        location_db_obj.radius = float(ali_result.radius)
        if (ali_result.latitiude != '') and (ali_result.longitude != ''):
            location_db_obj.location_point = [float(ali_result.latitiude), float(ali_result.longitude)]
        location_db_obj.location = ali_result.location

        location_db_obj.otcfield = ali_result.otcfield
        location_db_obj.psap_no = ali_result.psap_no
        location_db_obj.esn = ali_result.esn
        location_db_obj.postal = ali_result.postal
        location_db_obj.psap_name = ali_result.psap_name
        location_db_obj.pilot_no = ali_result.pilot_no

        location_db_obj.agencies_display = ali_result.agencies_display
        location_db_obj.fire_no = ali_result.fire_no
        location_db_obj.ems_no = ali_result.ems_no
        location_db_obj.police_no = ali_result.police_no

        location_db_obj.save()

        publish_update_location_success(room_number, ali_result)
    except Exception as e:
        stacktrace = traceback.format_exc()
        log.error("error in process_ali_success %r",e)
        log.error(stacktrace)


def ali_lookup(room_number, number, ali_format):
    d = send_ali_request(room_number, number, ali_format)

    def process_ali_failed(failure):
        log.debug("ali_failed number %r, %r", room_number, number)
        publish_update_location_failed(room_number)

    d.addErrback(process_ali_failed)
    d.addCallback(process_ali_success)


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


