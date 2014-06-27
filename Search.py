import re
import sys
import json
import logging
import time
import requests
from lxml import html
from SessionManager import SessionManager


def getLocationId(session,location):
    url = "http://www.okcupid.com/locquery?func=query&query=%s" % location
    result = eval(session.get(url).text)
    return result["locid"]

class SearchFilter(object):

    def genFilter(self):
        raise NotImplementedError

class PhotoFilter(SearchFilter):

    def __init__(self,required):
        self.__required =   required

    def genFilter(self):
        if self.__required:
            return "1,1"
        else:
            return "1,0"

class StatusFilter(SearchFilter):

    ANY         =   0
    SINGLE      =   2
    NOT_SINGLE  =   60

    def __init__(self,status):
        self.__status   =   status

    def genFilter(self):
        return "35,%s" % self.__status

class AgeFilter(SearchFilter):

    def __init__(self,lower,upper):
        self.__lower    =   lower
        self.__upper    =   upper

    def genFilter(self):
        return "2,%s,%s" % (self.__lower,self.__upper)

class RatingFilter(SearchFilter):
    def __init__(self,lower,upper):
        self.__lower    =   lower
        self.__upper    =   upper

    def genFilter(self):
        return "25,%s,%s" % (self.__lower,self.__upper)


class LastOnFilter(SearchFilter):

    NOW     =   3600
    DAY     =   86400
    WEEK    =   604800
    MONTH   =   2678400
    YEAR    =   31536000
    DECADE  =   315360000

    def __init__(self,time):
        self.__time =   time

    def genFilter(self):
        return "5,%s" % self.__time

class ZipCodeFilter(SearchFilter):

    VALID_DISTANCE = [5,10,25,50,100,250,500]

    def __init__(self,zip_code,distance):
        if distance not in ZipCodeFilter.VALID_DISTANCE:
            raise RuntimeError,"Invalid Distance [%s]" % distance
        self.__zipCode  =   zip_code
        self.__distance =   distance

    def genFilter(self):
        return "3,%d&lquery=%d" % (self.__distance,self.__zipCode)

class LocationIdFilter(SearchFilter):

    VALID_DISTANCE = [5,10,25,50,100,250,500]

    def __init__(self,locid,distance):
        if int(distance) not in ZipCodeFilter.VALID_DISTANCE:
            raise RuntimeError,"Invalid Distance [%s]" % distance
        self.__locId    =   locid
        if long(self.__locId) == 0:
            self.__distance =   32768
        else:
            self.__distance =   distance

    def genFilter(self):
        return "3,%s&locid=%s" % (self.__distance,self.__locId)

class LocationAnywhereFilter(object):

    def genFilter(self):
        return "locid=0"

class GentationFilter(SearchFilter):

    CONSTANTS = {
                    "girls who like guys"   :   34,
                    "guys who like girls"   :   17,
                    "girls who like girls"  :   40,
                    "guys who like guys"    :   20,
                    "both who like bi guys" :   54,
                    "both who like bi girls":   57,
                    "straight girls only"   :   2,
                    "straight guys only"    :   1,
                    "gay girls only"        :   8,
                    "gay guys only"         :   4,
                    "bi girls only"         :   32,
                    "bi guys only"          :   16,
                    "girls"                 :   34|8,
                    "guys"                  :   17|4,
                    "everybody"             :   63
                }

    def __init__(self,value):
        if isinstance(value,basestring):
            if value not in GentationFilter.CONSTANTS:
                raise RuntimeError,"Invalid Gentation Option [%s]" % value
            self.__value = value
        elif isinstance(value,int):
            self.__value    =   self.getGentationString(value)
        else:
            raise RuntimeError

    @staticmethod
    def getGentationString(value):
        for k,v in GentationFilter.CONSTANTS.iteritems():
            if v == value:
                return k

    @staticmethod
    def getGentation(value):
        return GentationFilter.CONSTANTS[value]

    @staticmethod
    def genGentation(gender,orientation):
        VALID_GENDERS       =   ["M","F"]
        VALID_ORIENTATIONS  =   ["Strait","Bisexual","Gay"]

        if gender == "M":
            if orientation == "Strait":
                gentation   =   "girls who like guys"
            elif orientation == "Bisexual":
                gentation   =   "both who like bi guys"
            elif orientation == "Gay":
                gentation   =   "guys who like guys"
            else:
                raise RuntimeError,"Invalid Orientation [%s]" % orientation
        elif gender == "F":
            if orientation == "Strait":
                gentation   =   "guys who like girls"
            elif orientation == "Bisexual":
                gentation   =   "both who like bi girls"
            elif orientation == "Gay":
                gentation   =   "girls who like girls"
            else:
                raise RuntimeError,"Invalid Orientation [%s]" % orientation
        else:
            raise RuntimeError,"Invalid Gender [%s]" % gender
        return gentation

    def genFilter(self):
        return "0,%d" % GentationFilter.CONSTANTS[self.__value]

class MatchOrder(object):

    VALID_ORDERS=["MATCH","ENEMY"]

    def __init__(self,order):
        if order not in MatchOrder.VALID_ORDERS:
            raise RuntimeError,"Invalid Order [%s]" % order
        self.__order = order

    def genFilter(self):
        return "matchOrderBy=%s" % self.__order

def genSearchURL(*args):
        url     = "http://www.okcupid.com/match?"
        filters = []


        for arg in args:
            if isinstance(arg,SearchFilter):
                filters.append(arg)
            else:
                url += "%s&" % arg.genFilter()

        for idx in range(len(filters)):
            url += "filter%d=%s&" % (idx+1,filters[idx].genFilter())

        #stuff we do not know what it does
        #@TODO - mygender is hardwired to m, should fix
        url += "custom_search=0&fromWhoOnline=0&mygender=m&update_prefs=1&sort_type=0&sa=1&using_saved_search="

        """
        "http://www.okcupid.com/match?filter1=0,63&filter2=2,18,98&filter3=5,2678400&filter4=1,1&locid=0&timekey=1&matchOrderBy=MATCH&custom_search=0&fromWhoOnline=0&mygender=m&update_prefs=1&sort_type=0&sa=1&using_saved_search=&count=5"
        """
        return url

def doSearchJSON(url):
    session =   SessionManager.getSession()
    pageSize    =   64
    rv  =   []
    

    i = 0
    timeKey = 1
    while True:
        newURL = url + "&timekey=%s&count=%s&low=%s&okc_api=1" % (timeKey,pageSize,(1+i*pageSize))
        if i == 0:
            newURL += "#Search"

        try:
            print newURL
            page = session.get(newURL)
        except requests.exceptions.ConnectionError:
            logging.warn("Connection error, sleeping 30 seconds")
            time.sleep(30)
            continue
        """
        print page
        print page.text
        print page.status_code
        print page.reason
        """
        if page.status_code != 200:
            logging.warn("Page Error [%s:%s] sleeping 60 seconds" % (page.status_code,page.reason))
            time.sleep(30)
            continue

        data        =   json.loads(page.text)
        data["url"] =   newURL
        logging.info("Search total_matches [%s] matches [%s]" % (data["total_matches"],len(data["amateur_results"])))
        if len(data["amateur_results"]) == 0:
            total = 0
            for v in rv:
                total += len(v["amateur_results"])
            logging.info("\tTotal [%s]" % total)

            return rv

        rv.append(data)
        timeKey    =   data["cache_timekey"]
        i+=1
        time.sleep(10)
