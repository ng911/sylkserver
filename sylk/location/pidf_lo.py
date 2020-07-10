# !/usr/local/bin/python2.7
'''
The main location module, uses 39peer's XML.
It can operate as a LIS (Location Information Server), HELD client and LoST client.
It also provides high-level classes for HELD, PIDF and PIDF-LO data.

@author: Kundan Singh
@contact: kundan10@gmail.com
@copyright: (c) 2011-2012, Intencity Cloud Technologies LLC
@copyright: (c) 2011-2012, Emergent Communications Inc

All rights reserved by Emergent Communications Inc.
'''
from xml.dom.minidom import parseString
try:
    from sylk.applications import ApplicationLogger
    log = ApplicationLogger(__package__)
except:
    import logging
    log = logging.getLogger("emergent-ng911")

presenceNS = "urn:ietf:params:xml:ns:pidf"
gpNS = "urn:ietf:params:xml:ns:pidf:geopriv10"
civicNS = "urn:ietf:params:xml:ns:pidf:geopriv10:civicAddr"
gmlNS = "http://www.opengis.net/gml"

def getCivicElements(parent, elements):
    ret = ()
    for element in elements:
        val = getCivicElement(parent, element)
        ret = ret + (val,)
    return ret

def getElementText(ns, parent, elementName):
    nodeVal = None
    node = parent.getElementsByTagNameNS(ns, elementName)
    if (node != None) and len(node) > 0:
        node = node[0]
        childNodes = node.childNodes
        if childNodes != None and len(childNodes) > 0:
            childNode = childNodes[0]
            if childNode.nodeType == node.TEXT_NODE:
                nodeVal = childNode.data
    return nodeVal

def getCivicElement(parent, elementName):
    return getElementText(civicNS, parent, elementName)

def combineAddressElements(elements):
    elements = [element for element in elements if element != None]
    return " ".join(elements)


def xml2display(str_xml):
    postal = community = state = latitude = longitude = radius = name = None
    xml = parseString(str_xml)
    location_resp = xml.getElementsByTagName("locationResponse")[0]

    presence = location_resp.getElementsByTagNameNS(presenceNS, "presence")[0]
    locationInfo = presence.getElementsByTagNameNS(gpNS, "location-info")[0]
    civicLocation = locationInfo.getElementsByTagNameNS(civicNS, "civicAddress")
    if civicLocation != None and len(civicLocation) > 0:
        civicLocation = civicLocation[0]
        country, state, county, city, a6, road, name, landmark, room, floor, house_no, house_no_suffix, postal_code, pod, prd, sts = getCivicElements(civicLocation, \
           ["country", "A1","A2", "A3", "A6", "RD", 'NAM', 'LMK', 'LOC', 'FLR', 'HNO', 'HNS', 'PC', 'POD', 'PRD', 'STS' ])
        housenum = combineAddressElements([house_no, house_no_suffix])
        street = combineAddressElements([road, a6, prd, pod, sts])
        if floor != None:
            floor =  floor + "th floor"
        streetaddr = combineAddressElements([landmark, housenum, street, floor, room])
        postal = combineAddressElements([name, streetaddr])
        community = combineAddressElements([county, city])

    point = locationInfo.getElementsByTagNameNS(gmlNS, "Point")
    if point != None and len(point) > 0:
        point = point[0]
        pos = getElementText(gmlNS, point, "pos")
        if pos != None:
            print ("pos is ", pos)
            posList = pos.split()
            if len(posList) > 1:
                latitude = float(posList[0])
                longitude = float(posList[1])

    circle = locationInfo.getElementsByTagNameNS(gmlNS, "Circle")
    if circle != None and len(circle) > 0:
        circle = circle[0]
        radius = getElementText(gmlNS, circle, "radius")
        if radius != None:
            radius = float(radius)

    return (postal, community, state, latitude, longitude, radius, name)




