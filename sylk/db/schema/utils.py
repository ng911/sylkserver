import arrow

def getIsoFormat(dateTimeObj):
    arrowDateTimeObj = arrow.get(dateTimeObj)
    return arrowDateTimeObj.format("YYYY-MM-DDTHH:mm:ss.SSSZ")


# this has higher precision for sub seconds
def getIsoMaxFormat(dateTimeObj):
    arrowDateTimeObj = arrow.get(dateTimeObj)
    return arrowDateTimeObj.format("YYYY-MM-DDTHH:mm:ss.SSSSSSZ")

