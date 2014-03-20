import optparse
import sys
import os
import re
import webbrowser
import time
import lxml.html.builder as E
import lxml.etree

from Experiment import MinerExperiment
from Questions import QuestionDB
from Profile import MatchProfile,UserProfile


class SearchData(object):

    def __init__(self,name):
        self.Name               =   name
        self.RawNames           =   []
        self.MatchNames         =   []   
        self.MatchProfiles      =   []
        self.MutualProfiles     =   []
        self.Charts             =   {}
        self.InfoCharts         =   {}

class ReportData(object):

    def __init__(self,experiment):
        self.Experiment     =   experiment
        self.SearchTypes    =   {}

        for searchType in experiment.getSearchTypes():
            self.SearchTypes[searchType] =   SearchData(searchType)

class ReportTable(object):

    def __init__(self,*args):
        self.__labels   =   []
        self.__cols     =   []

        for arg in args:
            self.__cols.append([])
            self.__labels.append(arg)

    def addRow(self,*args):
        for idx in range(len(args)):
            self.__cols[idx].append(args[idx])

    def getLabels(self):
        return self.__labels

    def getRowCount(self):
        return len(self.__cols[0])

    def getRow(self,idx):
        rv = []
        for col in self.__cols:
            rv.append(col[idx])
        return rv            

class ReportGraph(object):

    def __init__(self,stacked=False):
        self.__Data             =   {}
        self.__Stacked          =   stacked

    def setValue(self,x,value):
        self.__Data[x]      =   value

    def incValue(self,x,value):
        if x not in self.__Data:
            self.__Data[x]  =   0
        self.__Data[x]      +=  value

    def getValue(self,x):
        return self.__Data.get(x,0)

    def getKeys(self):
        return self.__Data.keys()

    def isStacked(self):
        return self.__Stacked

    def printStuff(self):
        sys.stderr.write("%s\n" % str(self.__Data))

class ReportManager(object):

    def __init__(self):
        self.__reportPath      =    os.path.join(os.path.dirname(sys.modules[__name__].__file__), "Reports")

        if not os.path.exists(self.__reportPath):
            sys.stderr.write("Report path does not exist, creating\n")
            os.mkdir(self.__reportPath)

    def __buildTable(self,title,table):
        tableArgs   =   []
        labelArgs   =   []
        for label in table.getLabels():
            labelArgs.append(E.TH(label))
        tableArgs.append(E.TR(*labelArgs))

        for idx in range(table.getRowCount()):
            rowArgs =   []
            for r in table.getRow(idx):
                if r is None:
                    rowArgs.append(E.TD(""))
                else:
                    rowArgs.append(E.TD("%s" % r))
            tableArgs.append(E.TR(*rowArgs))

        return E.DIV(E.H2(title),E.TABLE(*tableArgs))

    def __nextPowerOfTwo(self,value):
        rv = 16
        while True:
            if value < rv:
                return rv
            if rv >= 256:
                rv += 64
            elif rv >= 128:
                rv += 32
            else:
                rv += 16

    def __buildHorizontalChart(self,*args):
        assert isinstance(args[0],basestring)
        sys.stderr.write("Building hchart for [%s]\n" % args[0])
        reportCharts    =   []

        yValues =   []
        xMax    =   2
        for arg in args[1:]:
            reportCharts.append(arg)

        for z in range(len(reportCharts)):
            yValues = set(yValues) | set(reportCharts[z].getKeys())
            for key in reportCharts[z].getKeys():
                xValue  =   reportCharts[z].getValue(key)
                if reportCharts[z].isStacked():
                    for zz in reportCharts[z:]:
                        xValue += zz.getValue(key)
                xMax    =   max(xMax,xValue)
        xMax    =   self.__nextPowerOfTwo(xMax)

        if len(yValues) == 0:
            return E.DIV(E.H2(args[0]),E.SPAN("No Data"))

        yValues =   sorted(yValues,reverse=True)
        yMin    =   yValues[0]
        yMax    =   yValues[-1]

        chartArgs   =   [E.CLASS("hBarGraph")]
        chartKwargs =   {"style":"height: %spx" % ((30*len(yValues)))}

        idx = 0
        #if isinstance(yMin,int) and isinstance(yMax,int):
        #    labelRange  =   range(yMin,yMax+1)
        #else:
        labelRange  =   yValues

        for y in labelRange:
            chartArgs.append(E.LI("  %s  " % y,E.CLASS("p0"),style="width: 100%%; color: #000; bottom: %spx;" % (30*idx)))
            for z in range(len(reportCharts)):
                value   =   reportCharts[z].getValue(y)
                if value == 0:
                    x       =   0
                    value   =   ""

                elif reportCharts[z].isStacked():
                   
                    vSum  =   value
                    for zz in reportCharts[(z+1):]:
                        vSum += zz.getValue(y)
                    #sys.stderr.write("[%s] Index [%s] value [%s] vSum [%s]\n" % (y,z,value,vSum))
                    x       =   80.0 * float(vSum)/float(xMax)
                else:
                    x       =   80.0 * float(value)/float(xMax)
                chartArgs.append(E.LI("%s" % value,E.CLASS("p%d" % (z+1)),style="width: %s%%; bottom: %spx;" % (x,30*idx)))
            idx += 1
        chart       =   E.UL(*chartArgs,**chartKwargs)

        return E.DIV(E.H2(args[0]),chart)



    def __buildVerticalChart(self,*args):
        assert isinstance(args[0],basestring)

        reportCharts    =   []

        xValues =   []
        yMax    =   2
        for arg in args[1:]:
            xValues = set(xValues) | set(arg.getKeys())
            for key in arg.getKeys():
                yValue  =   arg.getValue(key)
                yMax    =   max(yMax,yValue)
            reportCharts.append(arg)
        yMax    =   self.__nextPowerOfTwo(yMax)

        xValues =   sorted(xValues)
        xMin    =   xValues[0]
        xMax    =   xValues[-1]

        chartArgs   =   [E.CLASS("vBarGraph")]
        xArgs       =   [E.CLASS("xAxis")]

        idx = 0
        if isinstance(xMin,int) and isinstance(xMax,int):
            labelRange  =   range(xMin,xMax+1)
        else:
            labelRange  =   xValues

        for x in labelRange:
            for z in range(len(reportCharts)):
                value   =   reportCharts[z].getValue(x)
                y       =   200.0 * float(value)/float(yMax)
                chartArgs.append(E.LI("%s" % value,E.CLASS("p%d" % (z+1)),style="height: %spx; left: %spx;" % (y,20*idx)))
            xArgs.append(E.LI("%s" % x))
            idx += 1
        chart       =   E.UL(*chartArgs)
        labels      =   E.UL(*xArgs)

        return E.DIV(E.H2(args[0]),chart,labels)

    def __buildIndexPage(self,data):

        if "Match" in data.SearchTypes.keys():
            defaultMatchPage = "Match.html"
        else:
            defaultMatchPage = "%s.html" % data.SearchTypes.keys()[0]

        html    =   E.HTML(
                        E.HEAD(
                            E.LINK(rel="stylesheet", type="text/css", href="../Assets/Report.css")
                        ),
                        E.BODY( 
                            E.CLASS("main"),
                            E.DIV(
                                E.IFRAME("",src="header.html",name="headerFrame",style="height: 100%; width: 100%;"),
                                id="header"
                            ),
                            E.DIV(
                                E.IFRAME("",src="navigation.html",name="navigationFrame",style="height: 100%; width: 100%;"),
                                id="navigation"
                            ),
                            E.DIV(
                                E.IFRAME("",src=defaultMatchPage,name="matchFrame",style="height: 100%; width: 100%;"),
                                id="content"
                            )
                        )
                    )
        return lxml.etree.tostring(html,pretty_print=True)

    def __buildHeaderPage(self,data):

        html    =   E.HTML(
                        E.HEAD( 
                            E.STYLE("body {background-color:#eeeeee;}")
                        ),
                        E.BODY(
                            E.P(
                                "User Name : %s" % data.Experiment.getUserName(),
                                E.BR(),
                                "Min Match : %s%%" % data.Experiment.getMinMatch(),
                                E.BR(),
                                "Age Range : %s-%s" % data.Experiment.getAgeRange(),
                                E.BR(),
                                "Gentation : %s" % data.Experiment.getGentation()
                            )
                        )
                    )
        return lxml.etree.tostring(html,pretty_print=True)

    def __buildNavigationPage(self,data):
        
        bodyArgs    =   [E.H2("Navigation")]
        for k in data.SearchTypes.keys():
            bodyArgs.append(E.DIV(E.A("[%s]" % k, href="%s.html" % k,target="matchFrame")))
 

        html    =   E.HTML(
                        E.HEAD(E.STYLE("body {background-color:#eeeeee;}")),
                        E.BODY(*bodyArgs)
                    )
        return lxml.etree.tostring(html,pretty_print=True)

    def __buildSearchTypePage(self,search_data):
        if search_data.Name == "Enemy":
            colour  =    "#FFC0C0"
        elif search_data.Name == "Match":
            colour  =    "#C0FFC0"
        else:
            raise RuntimeError

        bodyArgs    =   []
        bodyArgs.append(E.H2("Result Summary"))
        bodyArgs.append(E.P(
                            "Results : %s" % len(search_data.RawNames),
                            E.BR(),
                            "Matches : %s" % len(search_data.MatchNames),
                            E.BR(),
                            "Mutual  : %s" % len(search_data.MutualProfiles)
                            )
                        )
        bodyArgs.append(self.__buildVerticalChart("Result By Age",search_data.Charts["ResultAge"]))
        bodyArgs.append(self.__buildVerticalChart("Matches By Age",search_data.Charts["MatchAge"],search_data.Charts["MutualAge"]))
        for k in sorted(search_data.InfoCharts.keys()):
            v =  search_data.InfoCharts[k]
            bodyArgs.append(self.__buildHorizontalChart(k,*v))

        bodyArgs.append(self.__buildTable("Questions By Priority",search_data.Charts["Answers"]))
        bodyArgs.append(self.__buildTable("Words by Essay",search_data.Charts["Words"]))

        html    =   E.HTML(
                        E.HEAD( 
                            E.TITLE(search_data.Name),
                            E.LINK(rel="stylesheet", type="text/css", href="../Assets/Chart.css"),
                            E.STYLE("body {background-color:%s;}" % colour)
                        ),
                        E.BODY(*bodyArgs)
                    )
        return lxml.etree.tostring(html,pretty_print=True)

    def writeReport(self,name,data):
        basePath    =   os.path.join(self.__reportPath,name)
        if not os.path.exists(basePath):
            sys.stderr.write("Output path does not exist, creating\n")
            os.mkdir(basePath)
        indexPage   =   self.__buildIndexPage(data)
        output = open(os.path.join(basePath,"index.html"),"w")
        output.write(indexPage)
        output.close()

        headerPage   =   self.__buildHeaderPage(data)
        output = open(os.path.join(basePath,"header.html"),"w")
        output.write(headerPage)
        output.close()

        navPage     =   self.__buildNavigationPage(data)
        output = open(os.path.join(basePath,"navigation.html"),"w")
        output.write(navPage)
        output.close()

        for k,v in data.SearchTypes.iteritems():
            page   =   self.__buildSearchTypePage(v)
            output = open(os.path.join(basePath,"%s.html" % k),"w")
            output.write(page)
            output.close()


    def displayReport(self,name):
        fileName    =   os.path.join(self.__reportPath,name,"index.html")
        controller = webbrowser.get()
        controller.open_new("file:" + os.path.abspath(fileName))
  
class StatContainer(object):

    def __init__(self,qid):
        self.__qid      =   qid
        self.__weights  =   []

    def getId(self):
        return self.__qid

    def addWeight(self,weight):
        self.__weights.append(weight)

    def getCount(self):
        return len(self.__weights)

    def getScore(self):
        sum = 0.0
        for weight in self.__weights:
            sum += weight
        return sum
        #if sum > 0:
        #    return 100.0 * sum/float(self.getCount())
        #else:
        #    return 0.0

    def __cmp__(self,other):
        return cmp(self.getScore(),other.getScore())

def ProcessAnswers(profiles):
    aStats  =   {}
    for questionId in QuestionDB.getQuestionIds():
        aStats[questionId] = StatContainer(questionId)

    for profile in profiles:
        for idx in range(len(profile.Answers)):
            aStats[profile.Answers[idx]].addWeight( float(idx)/float(len(profile.Answers)))
    reportTable = ReportTable("Id","Count","Score","Text")
    sortedStats = sorted(aStats.values())
    for idx in range(128):
        aStat = sortedStats[len(sortedStats) - idx - 1]
        reportTable.addRow(aStat.getId(),aStat.getCount(),int(aStat.getScore()),QuestionDB.getText(aStat.getId()))

    return reportTable

def ProcessField(group,field,profiles,multi_value=False,skip_values=[],strip=None):
    rv = ReportGraph()
    for profile in profiles:
        groupDict   = getattr(profile,group)
        value       = groupDict[field]
        if strip is not None:
            value = value.replace(strip,"")
        if len(value) == 0:
            values = ["No Answer"]
        elif multi_value:
            splitList   =   re.split(",",value)
            values      =   []
            for x in splitList:
                if "(" in x:
                    x = x[:x.find("(")]
                values.append(x)
        else:
            commaIndex  = value.find(",")
            if commaIndex != -1:
                value = value[:commaIndex]
            values = [value]
        for value in values:
            if value not in skip_values: 
                rv.incValue(value.strip(),1)
    return rv

def SimpleProcessRatings(profiles):
    rv = ReportGraph()
    for i in range(5):
        rv.setValue(i,0)

    for profile in profiles:
        rating = int(profile.Info["Rating"])
        rv.incValue(rating,1)

    return rv

def ProcessRatings(group,field,profiles):
    rv = []
    for i in range(5):
        rv.append(ReportGraph(True))

    for profile in profiles:
        rating = int(profile.Info["Rating"])
        if rating == 0:
            continue
        groupDict   = getattr(profile,group)
        value       = groupDict[field]
        rv[rating-1].incValue(value,1)

    rv.reverse()
    return rv

def ProcessContactColour(group,field,profiles):
    cMap =  {
                "red":0,
                "yellow":3,
                "green":2,
                "last_contact":1
            }

    rv = []
    for i in range(len(cMap)):
        rv.append(ReportGraph(True))

    for profile in profiles:
        colour = profile.Info["ContactColour"]
        groupDict   = getattr(profile,group)
        value       = groupDict[field]
        rv[cMap[colour]].incValue(value,1)
    return rv

def ProcessEssays(profiles):
    #stripList   =   [',','.','\n','\r','/','(',')']
    stripList   =   ["the","i","m","me","and","to","a","you","of","do","for","to","is","that","than","my","im","it","but"]


    table   =   ReportTable( *[ "%s" % x for x in range(10) ])
    cols    =   []
    for i in range(10):
        essayDict   =   {}
        for profile in profiles:
            essayWords  =   profile.Essays[i]
            if essayWords is None:
                continue
            #sys.stderr.write("Essay [%s] Profile [%s] Words [%s]\n" % (i,profile.Info["Name"],essayWords))
            essayWords = re.sub(r'[^a-z ]','', essayWords.lower())
            for stripWord in stripList:
                essayWords.replace(stripWord,"")
            splitList   =   re.split(" ",essayWords)
            for essayWord in splitList:
                if essayWord in stripList:
                    continue
                if len(essayWord) < 5:
                    continue
                if essayWord not in essayDict:
                    essayDict[essayWord] = 0
                essayDict[essayWord] += 1
        #sys.stderr.write("Essay Dict %s\n" % essayDict)
        orderedWords    = sorted(essayDict,key=essayDict.get,reverse=True)
        while len(orderedWords) < 64:
            orderedWords.append(None)
        cols.append(orderedWords[:64])
        #sys.stderr.write("Col [%d] Entries [%d]\n" % (i,len(cols[i])))
 
    for j in range(0,64):
        values = [x[j] for x in cols]
        atLeastOne  =    False
        for v in values:
            if v is not None:
                atLeastOne = True
        if not atLeastOne:
            break
        table.addRow( *[x[j] for x in cols  ] )


    return table

def BuildPage(glob,local):
    html    =   E.HTML(
                        E.HEAD( 
                            E.TITLE(local["SearchType"]),
                            E.STYLE("body {background-color:#d0e4fe;}")
                        ),
                        E.BODY( E.CLASS("main"),
                            E.H2("Experiment Profile"),
                            E.P(
                                "User Name : %s" % glob["User"].Info["Name"],
                                E.BR(),
                                "Age Range : %s-%s" % (glob["AgeLow"],glob["AgeHigh"]),
                                E.BR(),
                                "Min Match : %s%%" % glob["Experiment"].getMinMatch(),
                            ),
                            E.H2("Result Summary"),
                            E.P(
                                "Results : %s" % local["TotalResult"],
                                E.BR(),
                                "Matches : %s" % local["TotalMatch"]
                            )
                        )
                )

    return lxml.etree.tostring(html,pretty_print=True)

if __name__ == "__main__":
    usage       =   "usage: %prog [options] folder"
    description =   "Views an experiment already run against OKCupid "
    parser = optparse.OptionParser(usage=usage,description=description)
    parser.add_option('-n', '--number', help="The top number of questions to output", type='int', default=128)

    options, args = parser.parse_args()

    if len(args) != 1:
        sys.stderr.write("Please supply folder name\n")
        sys.exit()      

    folderName      =   args[0]
    maxQuestions    =   16
    minAnswers      =   16
    profileAge      =   35


    if not os.path.exists(folderName):
        sys.stderr.write("No such folder [%s]\n" % folderName)
        sys.exit() 


    experiment  =   MinerExperiment()
    experiment.loadExperiment(folderName)
    reportData  =   ReportData(experiment)
    sys.stderr.write("Loaded Experiment for [%s]\n" % (experiment.getUserName()))
    sys.stderr.write("Total Questions [%s]\n" %  QuestionDB.getCount())

    userAge     =   int(experiment.getUserProfile().Info["Age"])
    #--------------------------------------------
    for searchType in experiment.getSearchTypes():
        searchData                      =   reportData.SearchTypes[searchType]
        searchData.Charts["ResultAge"]  =   ReportGraph()   
        searchData.Charts["MatchAge"]   =   ReportGraph()   
        searchData.Charts["MutualAge"]  =   ReportGraph()   
        for age,searchSet in experiment.getSearches(searchType).iteritems():
            searchData.RawNames += searchSet
            searchData.Charts["ResultAge"].setValue(age,len(searchSet))
            
        for profileName,fileName in experiment.getProfiles(searchType):
            searchData.MatchNames.append(profileName)
            matchProfile = MatchProfile()
            matchProfile.loadFromConfig(fileName)
            searchData.MatchProfiles.append(matchProfile)
            searchData.Charts["MatchAge"].incValue(int(matchProfile.Info["Age"]),1)
            if userAge < int(matchProfile.LookingFor["AgeLow"]):
                continue
            if userAge > int(matchProfile.LookingFor["AgeHigh"]):
                continue
            searchData.Charts["MutualAge"].incValue(int(matchProfile.Info["Age"]),1)
            searchData.MutualProfiles.append(matchProfile)

        searchData.Charts["Words"]          = ProcessEssays(searchData.MutualProfiles)
        searchData.Charts["Answers"]         = ProcessAnswers(searchData.MutualProfiles)
        searchData.InfoCharts["Ethnicity"]  = (ProcessField("Details","Ethnicity",searchData.MatchProfiles),ProcessField("Details","Ethnicity",searchData.MutualProfiles))

        searchData.InfoCharts["Relationship Type"]  = (ProcessField("Details","Relationship Type",searchData.MatchProfiles),ProcessField("Details","Relationship Type",searchData.MutualProfiles))
        searchData.InfoCharts["Smokes"]  = (ProcessField("Details","Smokes",searchData.MatchProfiles),ProcessField("Details","Smokes",searchData.MutualProfiles))
        searchData.InfoCharts["Religion"]  = (ProcessField("Details","Religion",searchData.MatchProfiles),ProcessField("Details","Religion",searchData.MutualProfiles))
        searchData.InfoCharts["Contact Colour"]  = (ProcessField("Info","ContactColour",searchData.MatchProfiles),ProcessField("Info","ContactColour",searchData.MutualProfiles))
        searchData.InfoCharts["Status"]  = (ProcessField("Info","Status",searchData.MatchProfiles),ProcessField("Info","Status",searchData.MutualProfiles))
        searchData.InfoCharts["Orientation"]  = (ProcessField("Details","Orientation",searchData.MatchProfiles),ProcessField("Details","Orientation",searchData.MutualProfiles))
        searchData.InfoCharts["Picture"]  = (ProcessField("Info","HasPicture",searchData.MatchProfiles),ProcessField("Info","HasPicture",searchData.MutualProfiles))
        searchData.InfoCharts["Sign"]  = (ProcessField("Details","Sign",searchData.MatchProfiles),ProcessField("Details","Sign",searchData.MutualProfiles))
        searchData.InfoCharts["Looking For - Status"]  = (ProcessField("LookingFor","Single",searchData.MatchProfiles),ProcessField("LookingFor","Single",searchData.MutualProfiles))
        searchData.InfoCharts["Looking For - Gentation"]  = (ProcessField("LookingFor","Gentation",searchData.MatchProfiles),ProcessField("LookingFor","Gentation",searchData.MutualProfiles))
        searchData.InfoCharts["Looking For - Near"]  = (ProcessField("LookingFor","Near",searchData.MatchProfiles),ProcessField("LookingFor","Near",searchData.MutualProfiles))
        searchData.InfoCharts["Looking For - Seeking"]  = (ProcessField("LookingFor","Seeking",searchData.MatchProfiles,multi_value=True,strip="For"),ProcessField("LookingFor","Seeking",searchData.MutualProfiles,multi_value=True,strip="For"))
        searchData.InfoCharts["Ratings"] = [SimpleProcessRatings(searchData.MatchProfiles)]
        searchData.InfoCharts["Ratings - By Age"] = ProcessRatings("Info","Age",searchData.MatchProfiles) 
        searchData.InfoCharts["Ratings - By %s" % searchType] = ProcessRatings("Percentages",searchType,searchData.MatchProfiles) 
        searchData.InfoCharts["Contact Colour - By Age"] = ProcessContactColour("Info","Age",searchData.MatchProfiles) 
        searchData.InfoCharts["Contact Colour - By %s" % searchType] = ProcessContactColour("Percentages",searchType,searchData.MatchProfiles) 
        searchData.InfoCharts["Languages other then English"] = (ProcessField("Details","Speaks",searchData.MatchProfiles,multi_value=True,skip_values=["English"]),ProcessField("Details","Speaks",searchData.MutualProfiles,multi_value=True,skip_values=["English"]))
    #--------------------------------------------
    reportName      =   os.path.basename(args[0])
    reportManager   =   ReportManager()
    reportManager.writeReport(reportName,reportData)
    reportManager.displayReport(reportName)
