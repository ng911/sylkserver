import re
from sylk.applications import ApplicationLogger

global log
log = ApplicationLogger(__package__)


def parse_warren_wireline(raw_ali):
    if (raw_ali == "") or (re.search("NO RECORD FOUND", raw_ali) != None):
        return ({}, "")
    log.info("raw_ali %s", raw_ali)
    lines = raw_ali.splitlines(True)
    '''
     1          1       CR                                                    
     2 - 32     31      Blank                                                 
     33         1       CR                                                    
     34 - 36    3       NPA                                                   
     37         1       Free Text                          -                  
     38 - 40    3       NXX                                                   
     41         1       Free Text                          -                  
     42 - 45    4       Calling Number                                        
     46 - 47    2       Blank                                                 
     48 - 55    8       Time (hh:mm:ss)                                       
     56         1       Blank                                                 
     57 - 58    2       Date--4 digit year                                    
     59 - 60    2       Date--4 digit year                                    
     61 - 64    4       Date--4 digit year                                    
     65         1       CR                                                 
    '''
    line = lines[2]
    npa = line[0:3]
    nxx = line[4:7]
    number = line[8:12]
    phone_number = '{}{}{}'.format(npa, nxx, number)
    '''
     66 - 97    32      Customer Name                                         
     98         1       CR                                                    
    '''
    line = lines[3]
    name = line
    '''
     99 - 108   10      House Number                                          
     109        1       Blank                                                 
     110 - 112  3       House Number Suffix                                   
     113        1       Blank                                                 
     114 - 116  3       Prefix Directional                                    
     117 - 125  9       Blank                                                 
     126 - 129  4       Class of service --4 character                        
     130        1       CR                                                
    '''
    line = lines[4]
    house_no = line[0:10]
    house_no_suffix = line[11:14]
    prefix_directional = line[15:18]
    class_of_service = line[19:]
    '''
    131 - 161  31      Street Name                                           
    162        1       CR
    '''
    line = lines[5]
    street_name = line

    '''
    163 - 171  9       Street Name                                           
    172        1       Blank                                                 
    173 - 176  4       Street Suffix                                         
    177 - 178  2       Blank                                                 
    179 - 181  3       Post Directional                                      
    182        1       Blank                                                 
    183 - 185  3       Free Text                          LEC                
    186        1       Blank                                                 
    187 - 191  5       Company ID1                                           
    192        1       CR                                                    
    '''
    line = lines[6]
    street_name_addtl = line[0:9]
    street_suffix = line[10:14]
    street = '{} {} {}'.format(street_name, street_name_addtl, street_suffix)
    post_directional = line[19:22]
    company_id = line[27:]
    '''
     193 - 220  28      Community Name                                        
     221        1       Blank                                                 
     222 - 223  2       State                                                 
     224        1       CR
     '''
    line = lines[7]
    community = line[0:28]
    state = line[29:]
    '''
    225 - 254  30      Location                                              
    255        1       CR                                                    
    '''
    line = lines[8]
    location = line

    '''
    256 - 275  20      Location                                              
    276 - 277  2       Blank                                                 
    278 - 280  3       Free Text                          ESN                
    281        1       Blank                                                 
    282 - 286  5       ESN - Leading zeros removed                           
    287        1       CR                                                    
    '''
    line = lines[9]
    location_extra = line[0:20]
    location = '{} {}'.format(location, location_extra)
    esn = line[26:]
    '''
    288 - 289  2       Free Text                          P#                 
    290 - 292  3       NPA                                                   
    293        1       Free Text                          -                  
    294 - 296  3       NXX                                                   
    297        1       Free Text                          -                  
    298 - 301  4       Calling Number                                        
    302        1       Blank                                                 
    303 - 306  4       Free Text                          ALT#               
    307 - 309  3       Blank                                                 
    310        1       Free Text                          -                  
    311 - 313  3       Blank                                                 
    314        1       Free Text                          -                  
    315 - 318  4       Blank                                                 
    319        1       CR
    '''
    line = lines[10]
    callback_npa = line[2:5]
    callback_nxx = line[6:9]
    callback = '{}{}{}'.format(callback_npa, callback_nxx, line[10:14])

    '''
    320        1       Free Text                          X                  
    321 - 332  12      Blank                                                 
    333        1       Free Text                          Y                  
    334 - 345  12      Blank                                                 
    346 - 347  2       Free Text                          CF                 
    348 - 350  3       Confidence Level                                      
    351        1       CR                                                    
    '''
    line = lines[11]
    x = line[0:1]
    y = line[13:14]
    '''
    352 - 354  3       Free Text                          UNC                
    355 - 361  7       Uncertainty                                           
    362        1       Blank                                                 
    363        1       Free Text                          Z                  
    364 - 370  7       Blank                                                 
    371 - 374  4       Free Text                          ZUNC               
    375 - 378  4       Blank                                                 
    379        1       CR                                                    
    '''
    line = lines[12]
    z= line[11:12]

    '''
    380 - 401  22      Law Info 1                                            
    402        1       Blank                                                 
    403 - 410  8       Law Info 2                                            
    411        1       CR                                                    
    '''
    line = lines[13]
    law = []
    law.append(line[0:22])
    law.append(line[23:])
    agenciesDisplay = line

    '''
    412 - 433  22      Fire Info 1                                           
    434        1       Blank                                                 
    435 - 442  8       Fire Info 2                                           
    443        1       CR                                                    
    '''
    line = lines[14]
    fire = []
    fire.append(line[0:22])
    fire.append(line[23:])
    agenciesDisplay = '{} {}'.format(agenciesDisplay, line)

    '''
    444 - 465  22      EMS Info 1                                            
    466        1       Blank                                                 
    467 - 474  8       EMS Info 2                                            
    475        1       CR                                                    
    '''
    line = lines[15]
    ems = []
    ems.append(line[0:22])
    ems.append(line[23:])
    agenciesDisplay = '{} {}'.format(agenciesDisplay, line)

    otcfield = ''
    psap_no = ''
    postal = ''
    psap_name = ''
    pilot_no = ''
    civic_address_data = {'state': state, 'name': name, 'phone_number': phone_number,
                          'latitude': x, 'longitude': y, 'radius': z,
                          'otcfield': otcfield, 'service_provider': company_id, 'psap_no': psap_no, 'esn': esn,
                          'community': community, 'postal': postal, 'psap_name': psap_name,
                          'class_of_service': class_of_service,
                          'pilot_no': pilot_no, 'service_provider': company_id, 'location': location,
                          "callback": callback,
                          'fire_no': fire[0], 'ems_no': ems[0], 'police_no': law[0],
                          'agencies_display': agenciesDisplay}

    civic_address_xml = ""
    if len(name) > 0: civic_address_xml = "<cl:NAME>%s</cl:NAME>" % (name)
    if len(house_no) > 0: civic_address_xml = "%s<cl:HNO>%s</cl:HNO>" % (civic_address_xml, house_no)
    if len(house_no_suffix) > 0: civic_address_xml = "%s<cl:HNS>%s</cl:HNS>" % (civic_address_xml, house_no_suffix)
    if len(post_directional) > 0: civic_address_xml = "%s<cl:PRD>%s</cl:PRD>" % (civic_address_xml, post_directional)
    if len(state) > 0: civic_address_xml = "%s<cl:A1>%s</cl:A1>" % (civic_address_xml, state)
    if len(community) > 0: civic_address_xml = "%s<cl:A3>%s</cl:A3>" % (civic_address_xml, community)
    if len(street) > 0: civic_address_xml = "%s<cl:A6>%s</cl:A6>" % (civic_address_xml, street)
    if len(location) > 0: civic_address_xml = "%s<cl:LOC>%s</cl:LOC>" % (civic_address_xml, location)
    if len(x) > 0: civic_address_xml = "%s<cl:CIRCLE><cl:POS>%s %s</cl:POS><cl:RADIUS>%s</cl:RADIUS></cl:CIRCLE>" % (
    civic_address_xml, x, y, z)

    civic_address_xml = "<cl:civicAddress xmlns:cl='urn:ietf:params:xml:ns:pidf:geopriv10:civicAddr'>%s</cl:civicAddress>" % (
    civic_address_xml)
    return (civic_address_data, civic_address_xml)


def parse_warren_wireless(raw_ali):
    if (raw_ali == "") or (re.search("NO RECORD FOUND", raw_ali) != None):
        return ({}, "")
    lines = raw_ali.splitlines(True)
    '''
    1          1       CR                                                    
    2 - 32     31      Blank                                                 
    33         1       CR                                                    
    '''
    '''
    34 - 36    3       Callback (NPA)                                        
    37         1       Free Text                          -                  
    38 - 40    3       Callback (NXX)                                        
    41         1       Free Text                          -                  
    42 - 45    4       Callback (Calling Number)                             
    46 - 47    2       Blank                                                 
    48 - 55    8       Time (hh:mm:ss)                                       
    56         1       Blank                                                 
    57 - 58    2       Date--4 digit year                                    
    59 - 60    2       Date--4 digit year                                    
    61 - 64    4       Date--4 digit year                                    
    65         1       CR                                                    
    '''
    i = 2
    line = lines[i]
    npa = line[0:3]
    nxx = line[4:7]
    number = line[8:12]
    phone_number = '{}{}{}'.format(npa, nxx, number)

    '''
    66 - 97    32      Customer Name                                         
    98         1       CR                                                    
    '''
    i = i+1
    line = lines[i]
    name = line

    '''
    99 - 108   10      House Number                                          
    109        1       Blank                                                 
    110 - 112  3       House Number Suffix                                   
    113        1       Blank                                                 
    114 - 116  3       Prefix Directional                                    
    117 - 125  9       Blank                                                 
    126 - 129  4       Class of service --4 character                        
    130        1       CR                                                    
    '''
    i = i+1
    line = lines[i]
    house_no = line[0:10]
    house_no_suffix = line[11:14]
    prefix_directional = line[15:18]
    class_of_service = line[19:]

    '''
    131 - 161  31      Street Name                                           
    162        1       CR                                                    
    '''
    i = i+1
    line = lines[i]
    street_name = line

    '''
    163 - 171  9       Street Name                                           
    172        1       Blank                                                 
    173 - 176  4       Street Suffix                                         
    177 - 178  2       Blank                                                 
    179 - 181  3       Post Directional                                      
    182        1       Blank                                                 
    183 - 185  3       Free Text                          LEC                
    186        1       Blank                                                 
    187 - 191  5       Company ID1                                           
    192        1       CR                                                    
    '''
    i = i+1
    line = lines[i]
    street_name_addtl = line[0:9]
    street_suffix = line[10:14]
    street = '{} {} {}'.format(street_name, street_name_addtl, street_suffix)
    post_directional = line[19:22]
    company_id = line[27:]

    '''
    193 - 220  28      Community Name                                        
    221        1       Blank                                                 
    222 - 223  2       State                                                 
    224        1       CR                                                    
    '''
    i = i+1
    line = lines[i]
    community = line[0:28]
    state = line[29:]

    '''
    225 - 254  30      Location                                              
    255        1       CR                                                    
    '''
    i = i+1
    line = lines[i]
    location = line

    '''
    256 - 275  20      Location                                              
    276 - 277  2       Blank                                                 
    278 - 280  3       Free Text                          ESN                
    281        1       Blank                                                 
    282 - 286  5       ESN - Leading zeros removed                           
    287        1       CR                                                    
    '''
    i = i+1
    line = lines[i]
    location_extra = line[0:20]
    location = '{} {}'.format(location, location_extra)
    esn = line[26:]

    '''
    288 - 289  2       Free Text                          P#                 
    290 - 292  3       Callback (NPA)                                        
    293        1       Free Text                          -                  
    294 - 296  3       Callback (NXX)                                        
    297        1       Free Text                          -                  
    298 - 301  4       Callback (Calling Number)                             
    302        1       Blank                                                 
    303 - 306  4       Free Text                          ALT#               
    307 - 309  3       NPA                                                   
    310        1       Free Text                          -                  
    311 - 313  3       NXX                                                   
    314        1       Free Text                          -                  
    315 - 318  4       Calling Number                                        
    319        1       CR                                                    
    '''
    i = i+1
    line = lines[i]
    callback_npa = line[2:5]
    callback_nxx = line[6:9]
    callback = '{}{}{}'.format(callback_npa, callback_nxx, line[10:14])

    alternate_npa = line[19:22]
    alternate_nxx = line[23:25]
    alternate_number = '{}{}{}'.format(alternate_npa, alternate_nxx, line[26:])
    '''
    320        1       Free Text                          X                  
    321 - 331  11      X Coordinate                                          
    332        1       Blank                                                 
    333        1       Free Text                          Y                  
    334 - 344  11      Y Coordinate                                          
    345        1       Blank                                                 
    346 - 347  2       Free Text                          CF                 
    348 - 350  3       Confidence Level                                      
    351        1       CR                                                    
    '''
    i = i+1
    line = lines[i]
    latitude = line[1:12]
    latitude = latitude.strip()
    log.info("latitude '%s'", latitude)
    if len(latitude) == 0:
        latitude = 0

    longitude = line[15:26]
    longitude = longitude.strip()
    if len(longitude) == 0:
        longitude = 0
    log.info("longitude '%s'", longitude)
    confidence = line[29:32]
    '''
    352 - 354  3       Free Text                          UNC                
    355 - 361  7       Uncertainty                                           
    362        1       Blank                                                 
    363        1       Free Text                          Z                  
    364 - 369  6       Z Coordinate                                          
    370        1       Blank                                                 
    371 - 374  4       Free Text                          ZUNC               
    375 - 378  4       Blank                                                 
    379        1       CR                                                    
    '''
    i = i+1
    line = lines[i]
    uncertainty = line[3:10]
    radius = line[12:18]

    '''
    380 - 401  22      Law Info 1                                            
    402        1       Blank                                                 
    403 - 410  8       Law Info 2                                            
    411        1       CR                                                    
    '''
    i = i+1
    line = lines[i]
    law = []
    law.append(line[0:22])
    law.append(line[23:])
    agenciesDisplay = line

    '''
    412 - 433  22      Fire Info 1                                           
    434        1       Blank                                                 
    435 - 442  8       Fire Info 2                                           
    443        1       CR                                                    
    '''
    i = i+1
    line = lines[i]
    fire = []
    fire.append(line[0:22])
    fire.append(line[23:])
    agenciesDisplay = '{} {}'.format(agenciesDisplay, line)

    '''
    444 - 465  22      EMS Info 1                                            
    466        1       Blank                                                 
    467 - 474  8       EMS Info 2                                            
    475        1       CR              
    '''
    i = i+1
    line = lines[i]
    ems = []
    ems.append(line[0:22])
    ems.append(line[23:])
    agenciesDisplay = '{} {}'.format(agenciesDisplay, line)

    otcfield = ''
    psap_no = ''
    postal = ''
    psap_name = ''
    pilot_no = ''
    civic_address_data = {'state': state, 'name': name, 'phone_number': phone_number,
                          'latitude': latitude, 'longitude': longitude, 'radius': radius,
                          'otcfield': otcfield, 'service_provider': company_id, 'psap_no': psap_no, 'esn': esn,
                          'community': community, 'postal': postal, 'psap_name': psap_name,
                          'class_of_service': class_of_service,
                          'pilot_no': pilot_no, 'service_provider': company_id, 'location': location,
                          "callback": callback,
                          'fire_no': fire[0], 'ems_no': ems[0], 'police_no': law[0],
                          'agencies_display': agenciesDisplay}

    civic_address_xml = ""
    if len(name) > 0: civic_address_xml = "<cl:NAME>%s</cl:NAME>" % (name)
    if len(house_no) > 0: civic_address_xml = "%s<cl:HNO>%s</cl:HNO>" % (civic_address_xml, house_no)
    if len(house_no_suffix) > 0: civic_address_xml = "%s<cl:HNS>%s</cl:HNS>" % (civic_address_xml, house_no_suffix)
    if len(post_directional) > 0: civic_address_xml = "%s<cl:PRD>%s</cl:PRD>" % (civic_address_xml, post_directional)
    if len(state) > 0: civic_address_xml = "%s<cl:A1>%s</cl:A1>" % (civic_address_xml, state)
    if len(community) > 0: civic_address_xml = "%s<cl:A3>%s</cl:A3>" % (civic_address_xml, community)
    if len(street) > 0: civic_address_xml = "%s<cl:A6>%s</cl:A6>" % (civic_address_xml, street)
    if len(location) > 0: civic_address_xml = "%s<cl:LOC>%s</cl:LOC>" % (civic_address_xml, location)
    if len(longitude) > 0: civic_address_xml = "%s<cl:CIRCLE><cl:POS>%s %s</cl:POS><cl:RADIUS>%s</cl:RADIUS></cl:CIRCLE>" % (
    civic_address_xml, longitude, latitude, radius)

    civic_address_xml = "<cl:civicAddress xmlns:cl='urn:ietf:params:xml:ns:pidf:geopriv10:civicAddr'>%s</cl:civicAddress>" % (
    civic_address_xml)

    return (civic_address_data, civic_address_xml)

