import re
import sys
from lxml import html


def getLocationId(session,location):
    url = "http://www.okcupid.com/locquery?func=query&query=%s" % location
    result = eval(session.get(url).text)
    return result["locid"]

class SearchFilter(object):

    def genFilter(self):
        raise NotImplementedError


class AgeFilter(SearchFilter):

    def __init__(self,lower,upper):
        self.__lower    =   lower
        self.__upper    =   upper

    def genFilter(self):
        return "2,%s,%s" % (self.__lower,self.__upper)

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
        self.__distance =   distance

    def genFilter(self):
        return "3,%s&locid=%s" % (self.__distance,self.__locId)

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
                    "everybody"             :   63
                }

    def __init__(self,value):
        if value not in GentationFilter.CONSTANTS:
            raise RuntimeError,"Invalid Gentation Option [%s]" % value
        self.__value = value

    def genFilter(self):
        return "0,%d" % GentationFilter.CONSTANTS[self.__value]


class TargetedGentationFilter(GentationFilter):


    VALID_GENDERS       =   ["M","F"]
    VALID_ORIENTATIONS  =   ["Strait","Bisexual","Gay"]

    def __init__(self,gender,orientation):
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

        super(TargetedGentationFilter,self).__init__(gentation)

def genSearchURL(*args):
        url     = "http://www.okcupid.com/match?matchOrderBy=MATCH&"
        filters = []

        for arg in args:
            if isinstance(arg,SearchFilter):
                filters.append(arg)

        for idx in range(len(filters)):
            url += "filter%d=%s&" % (idx+1,filters[idx].genFilter())

        #stuff we do not know what it does
        #url += "update_prefs=0"
        url += "custom_search=0&fromWhoOnline=0&mygender=m&update_prefs=1&sort_type=0&sa=1&using_saved_search="

        """
        "http://www.okcupid.com/match?filter1=0,63&filter2=2,18,98&filter3=5,2678400&filter4=1,1&locid=0&timekey=1&matchOrderBy=MATCH&custom_search=0&fromWhoOnline=0&mygender=m&update_prefs=1&sort_type=0&sa=1&using_saved_search=&count=5"
        """
        return url

class SearchResult(object):

    def __init__(self,name,percent,age):
        self.Name       =   name
        self.Percent    =   percent
        self.Age        =   int(age)

    def __cmp__(self,other):
        return cmp(other.Percent,self.Percent)

def doSearch(session,url):
    cutOff      =   0
    pageSize    =   32
    rv  =   []
    

    #TODO - we need to figure out timekey
    i = 0
    time = 1
    while True:
        newURL = url + "&timekey=%s&count=%s&low=%s" % (time,pageSize,(1+i*pageSize))
        if i == 0:
            newURL += "#Search"

        sys.stderr.write("URL [%s]\n" % (newURL)) 
        page = session.get(newURL)
        sys.stderr.write("Page [%s] [%s:%s] [%s]\n" % (i,page.status_code,page.reason,page.url))
        time,_ = re.search('CurrentGMT = new Date\(([\d]+)\*([\d]+)\)',page.text).groups()
        sys.stderr.write("Index [%s]\n" % time)
        #gmtIndex = page.text.find("CurrentGMT")
        #sys.stderr.write("GMTIndex [%d]\n" % gmtIndex)

        tree        =   html.fromstring(page.text)
        userNames   =   tree.xpath('//div[@class="username"]/a/text()')
        userAges    =   tree.xpath('//div[@class="userinfo"]/span[@class="age"]/text()')
        userLocs    =   tree.xpath('//div[@class="userinfo"]/span[@class="location"]/text()')
        rawPercents =   tree.xpath('//div[@class="match_card_text"]/div/text()')
        percents    =   [] 
        for raw in rawPercents:
            idx = raw.find('%')
            if idx != -1:
                percents.append(int(raw[:idx]))

        if len(userNames) != len(percents):
            raise RuntimeError,"Mismatch between Match [%s] and Profiles [%s]" % (len(percents),len(userNames))

        for idx in range(len(userNames)):
            rv.append( SearchResult(userNames[idx],percents[idx],userAges[idx]) )
            sys.stderr.write("[%3d%%] - %s - %s - %s\n" % (percents[idx],userAges[idx],userNames[idx],userLocs[idx]))

        #rv  +=  userNames
        if len(percents) != 0 and percents[-1] > cutOff and len(percents) == pageSize:
            i+=1
        else:
            break

    #sys.stderr.write("[%s] Results\n" % len(rv))
    return rv
