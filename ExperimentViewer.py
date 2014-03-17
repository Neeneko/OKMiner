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

    def __init__(self):
        self.__Data               =   {}

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
                rowArgs.append(E.TD("%s" % r))
            tableArgs.append(E.TR(*rowArgs))

        return E.DIV(E.H2(title),E.TABLE(*tableArgs))

    def __buildHorizontalChart(self,*args):
        assert isinstance(args[0],basestring)

        reportCharts    =   []

        yValues =   []
        xMax    =   64
        for arg in args[1:]:
            yValues = set(yValues) | set(arg.getKeys())
            for key in arg.getKeys():
                xValue  =   arg.getValue(key)
                xMax    =   max(xMax,xValue)
            reportCharts.append(arg)
        xMax    =   float(64 + xMax - xMax%64)

        yValues =   sorted(yValues)
        yMin    =   yValues[0]
        yMax    =   yValues[-1]

        #sys.stderr.write("================================\n")
        #for z in range(len(reportCharts)):
        #    reportCharts[z].printStuff()
        #sys.stderr.write("================================\n")

        chartArgs   =   [E.CLASS("hBarGraph")]
        chartKwargs =   {"style":"height: %spx" % (30*len(yValues))}

        idx = 0
        if isinstance(yMin,int) and isinstance(yMax,int):
            labelRange  =   range(yMin,yMax+1)
        else:
            labelRange  =   yValues

        for y in labelRange:
            chartArgs.append(E.LI("  %s  " % y,E.CLASS("p0"),style="width: 100%%; color: #000; bottom: %spx;" % (30*idx)))
            for z in range(len(reportCharts)):
                value   =   reportCharts[z].getValue(y)
                x       =   80.0 * float(value)/float(xMax)
                chartArgs.append(E.LI("%s" % value,E.CLASS("p%d" % (z+1)),style="width: %s%%; bottom: %spx;" % (x,30*idx)))
            idx += 1
        chart       =   E.UL(*chartArgs,**chartKwargs)

        return E.DIV(E.H2(args[0]),chart)



    def __buildVerticalChart(self,*args):
        assert isinstance(args[0],basestring)

        reportCharts    =   []

        xValues =   []
        yMax    =   64
        for arg in args[1:]:
            xValues = set(xValues) | set(arg.getKeys())
            for key in arg.getKeys():
                yValue  =   arg.getValue(key)
                yMax    =   max(yMax,yValue)
            reportCharts.append(arg)
        yMax    =   float(64 + yMax - yMax%64)

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

    def __buildIndexPage(self):
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
                                E.IFRAME("",src="Match.html",name="matchFrame",style="height: 100%; width: 100%;"),
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
        html    =   E.HTML(
                        E.HEAD( 
                            E.STYLE("body {background-color:#eeeeee;}")
                        ),
                        E.BODY(
                            E.H2("Navigation"),
                            E.DIV(
                                E.A("[Match]", href="Match.html",target="matchFrame")
                            ),
                            E.DIV(
                                E.A("[Enemy]", href="Enemy.html",target="matchFrame")
                            ),
                            E.DIV(
                                E.A("[Friend]", href="Friend.html",target="matchFrame")
                            )
                        )
                    )
        return lxml.etree.tostring(html,pretty_print=True)

    def __buildSearchTypePage(self,search_data):
        if search_data.Name == "Friend":
            colour  =    "#C0FFC0"
        elif search_data.Name == "Enemy":
            colour  =    "#FFC0C0"
        elif search_data.Name == "Match":
            colour  =    "#C0C0FF"
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
        #bodyArgs.append(self.__buildHorizontalChart("Ethnicity",search_data.Charts["MatchEthnicity"]))
        #bodyArgs.append(self.__buildHorizontalChart("Ethnicity",search_data.Charts["MatchEthnicity"],search_data.Charts["MutualEthnicity"]))
        for k,v in search_data.InfoCharts.iteritems():
            bodyArgs.append(self.__buildHorizontalChart(k,*v))

        bodyArgs.append(self.__buildTable("Questions By Priority",search_data.Charts["Answers"]))

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
        indexPage   =   self.__buildIndexPage()
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

def ProcessField(group,field,profiles):
    rv = ReportGraph()
    for profile in profiles:
        groupDict   = getattr(profile,group)
        value       = groupDict[field]
        commaIndex  = value.find(",")
        if commaIndex != -1:
            value = value[:commaIndex]
        elif len(value) == 0:
            value = "No Answer"
        rv.incValue(value,1)
    return rv

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
        searchData.Charts["Answers"]         = ProcessAnswers(searchData.MutualProfiles)
        searchData.InfoCharts["Ethnicity"]  = (ProcessField("Details","Ethnicity",searchData.MatchProfiles),ProcessField("Details","Ethnicity",searchData.MutualProfiles))

        searchData.InfoCharts["Relationship Type"]  = (ProcessField("Details","Relationship Type",searchData.MatchProfiles),ProcessField("Details","Relationship Type",searchData.MutualProfiles))
        searchData.InfoCharts["Smokes"]  = (ProcessField("Details","Smokes",searchData.MatchProfiles),ProcessField("Details","Smokes",searchData.MutualProfiles))
        searchData.InfoCharts["Religion"]  = (ProcessField("Details","Religion",searchData.MatchProfiles),ProcessField("Details","Religion",searchData.MutualProfiles))
        searchData.InfoCharts["Status"]  = (ProcessField("Info","Status",searchData.MatchProfiles),ProcessField("Info","Status",searchData.MutualProfiles))
        searchData.InfoCharts["Orientation"]  = (ProcessField("Info","Orientation",searchData.MatchProfiles),ProcessField("Info","Orientation",searchData.MutualProfiles))
        searchData.InfoCharts["Picture"]  = (ProcessField("Info","HasPicture",searchData.MatchProfiles),ProcessField("Info","HasPicture",searchData.MutualProfiles))
        searchData.InfoCharts["Sign"]  = (ProcessField("Details","Sign",searchData.MatchProfiles),ProcessField("Details","Sign",searchData.MutualProfiles))
        searchData.InfoCharts["Looking For - Status"]  = (ProcessField("LookingFor","Single",searchData.MatchProfiles),ProcessField("LookingFor","Single",searchData.MutualProfiles))
        searchData.InfoCharts["Looking For - Gentation"]  = (ProcessField("LookingFor","Gentation",searchData.MatchProfiles),ProcessField("LookingFor","Gentation",searchData.MutualProfiles))
        searchData.InfoCharts["Looking For - Near"]  = (ProcessField("LookingFor","Near",searchData.MatchProfiles),ProcessField("LookingFor","Near",searchData.MutualProfiles))
 
    #--------------------------------------------

    reportName      =   os.path.basename(args[0])
    reportManager   =   ReportManager()
    reportManager.writeReport(reportName,reportData)
    reportManager.displayReport(reportName)
