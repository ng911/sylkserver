
def get_location_display(location_db_obj):
    location_display = ''
    if (location_db_obj.postal is not None) and (location_db_obj.postal != ''):
        location_display = location_db_obj.postal
    if (location_db_obj.community is not None) and (location_db_obj.community != ''):
        if location_display == '':
            location_display = location_db_obj.community
        else:
            location_display = "%s, %s" % (location_display, location_db_obj.community)

    if (location_db_obj.state is not None) and (location_db_obj.state != ''):
        if location_display == '':
            location_display = location_db_obj.state
        else:
            location_display = "%s, %s" % (location_display, location_db_obj.state)
    return location_display
