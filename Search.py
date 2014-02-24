import sys
from lxml import html

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

def genSearchURL(*args):
        url     = "http://www.okcupid.com/match?matchOrderBy=MATCH&"
        filters = []

        for arg in args:
            if isinstance(arg,SearchFilter):
                filters.append(arg)

        for idx in range(len(filters)):
            url += "filter%d=%s&" % (idx+1,filters[idx].genFilter())

        #url += "count=512&"
        #url += "count=512&"
        url += "update_prefs=0"

        """
        "http://www.okcupid.com/match?filter1=0,63&filter2=2,18,98&filter3=5,2678400&filter4=1,1&locid=0&timekey=1&matchOrderBy=MATCH&custom_search=0&fromWhoOnline=0&mygender=m&update_prefs=1&sort_type=0&sa=1&using_saved_search=&count=5"
        """
        return url

def doSearch(session,url):
    cutOff      =   0
    pageSize    =   32
    rv  =   []
    
    #for i in range(32):
    i = 0
    while True:
        #sys.stderr.write("Page [%s]\n" % i)
        page = session.getSession().get(url + "&count=%s&low=%s" % (pageSize,(1+i*pageSize)))
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
            rv.append( (userNames[idx],percents[idx]) )
            #sys.stderr.write("[%3d%%] - %s - %s - %s\n" % (percents[idx],userAges[idx],userNames[idx],userLocs[idx]))

        
        #rv  +=  userNames
        if percents[-1] > cutOff and len(percents) == pageSize:
            i+=1
        else:
            break

    #sys.stderr.write("[%s] Results\n" % len(rv))
    return rv
