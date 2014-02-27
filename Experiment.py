import datetime
import os
import sys
import ConfigParser

from Questions import MinerQuestions
from ProfileManager import ProfileManager
from Profile import UserProfile,MatchProfile
from Search import *

class   MinerExperiment(object):

    PROPERTIES  =   {
                        "UserName"      : None,
                        "MaxResult"     : None,
                        "MinMatch"      : "80",
                        "Radius"        : "50",
                        "AgeRange"      : "10",
                        "AgeMin"        : None,
                        "AgeMax"        : None,
                        "Orientation"   : None,
                        "SkipVisit"     : False
                    }

    @staticmethod
    def getValidProperties():
        return MinerExperiment.PROPERTIES.keys()

    def __init__(self):
        self.__dataPath     =   os.path.join(os.path.dirname(sys.modules[__name__].__file__), "Data")
        self.__config       =   ConfigParser.ConfigParser()
        self.__config.optionxform=str
        if not os.path.exists(self.__dataPath):
            sys.stderr.write("Data path does not exist, creating\n")
            os.mkdir(self.__dataPath)
        self.__questions    =   MinerQuestions()
        self.__userProfile  =   UserProfile()

    def getSkipVisit(self):
        return bool(self.__config.get("Settings","SkipVisit"))

    def getMaxResults(self):
        try:
            rv = int(self.__config.get("Settings","MaxResult"))
        except:
            rv = -1
        return rv

    def getMinMatch(self):
        try:
            rv = int(self.__config.get("Settings","MinMatch"))
        except:
            rv = -1
        return rv

    def createExperiment(self,properties):
        expDir = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        self.__expPath      =   os.path.join(self.__dataPath,expDir)
        self.__configName   =   os.path.join(self.__expPath,"experiment.ini")

        os.mkdir(self.__expPath)
        self.__config.add_section("Settings")
        self.__config.add_section("Searches")
        self.__config.add_section("Matches")

        for k,v in MinerExperiment.PROPERTIES.iteritems():
            if k in properties.keys():
                self.__config.set("Settings",k,properties[k])
            else:
                self.__config.set("Settings",k,v)

        self.saveConfig()

    def saveConfig(self):
       with open(self.__configName,'wb') as configFile:
            self.__config.write(configFile)

    def loadConfig(self,config_name):
        self.__config.read(config_name)

    def loadExperiment(self,folder_name):
        self.__expPath      =   folder_name
        configName          =   os.path.join(self.__expPath,"experiment.ini")

        if not os.path.exists(configName):
            raise RuntimeError,"No experiment config found in folder"

        self.loadConfig(configName)

    def getUserName(self):
        return self.__config.get("Settings","UserName")

    def getExperimentPath(self):
        return self.__expPath
        
    def saveSearchURL(self,url):
        urlCount = len(self.__config.options("Searches"))
        self.__config.set("Searches","Search_%d" % (urlCount + 1),url) 
        self.saveConfig()
        
    def saveMatch(self,match_name,match_file_name):
        self.__config.set("Matches",match_name,match_file_name)
        self.saveConfig()

    def getMatchCount(self):
        return len(self.__config.options("Matches"))
 
    def getMatches(self):
        return self.__config.items("Matches")

    def doExperiment(self):
        sys.stderr.write("Starting Experiment against profile [%s]\n" % self.getUserName())
        profileManager  =   ProfileManager()
        session         =   profileManager.doLogin(self.getUserName())


        self.__userProfile.loadFromSession(session,self.getUserName())
        fileName        =   "%s.ini" %  self.__userProfile.Info["Name"] 
        fullName        =   os.path.join(self.getExperimentPath(),fileName)
        self.__userProfile.saveProfile(fullName)
        for question in self.__userProfile.Questions:
            if not self.__questions.hasQuestion(question.Id):
                self.__questions.addQuestion(question.Id,question.Text,question.Answers)
        self.__questions.saveQuestions()

        if self.__config.get("Settings","Orientation") is not None:
            orientation = self.__config.get("Settings","Orientation") 
        else:
            orientation = self.__userProfile.Info["Orientation"]

        gender          = self.__userProfile.Info["Gender"]
        radius          = self.__config.get("Settings","Radius")
        locationId      = getLocationId(session,self.__userProfile.Info["Location"])
        baseAge         = int(self.__userProfile.Info["Age"])
        
        if self.__config.get("Settings","AgeRange") is None:
            ageHigh =   baseAge
            ageLow  =   baseAge
        else:
            ageHigh =   baseAge+int(self.__config.get("Settings","AgeRange"))
            ageLow  =   baseAge-int(self.__config.get("Settings","AgeRange"))


        if self.__config.get("Settings","AgeMin") is not None:
            ageLow  =   int(self.__config.get("Settings","AgeMin"))

        if self.__config.get("Settings","AgeMax") is not None:
            ageHigh =   int(self.__config.get("Settings","AgeMax"))


        #TODO - age based slicing
        searchResults   =   []
        for i in range(ageLow,ageHigh+1):
        #for i in range(24,26):
            url = genSearchURL(AgeFilter(i,i),LastOnFilter(LastOnFilter.WEEK),LocationIdFilter(locationId,radius),TargetedGentationFilter(gender,orientation))

            sys.stderr.write("Search [%s]\n" % url)

            oneSearch       =   doSearch(session,url)
            searchResults   +=  oneSearch
            sys.stderr.write("Slice [%s] Results [%s] Cumulative [%s]\n" % (i,len(oneSearch),len(searchResults)))
        sys.stderr.write("Before Cut [%s] Results\n" % len(searchResults))
        count           =   0
        matchNames      =   []
        for searchResult in sorted(searchResults):
           
            if self.getMinMatch() != -1 and searchResult.Percent < self.getMinMatch():
                continue
            if self.getMaxResults() != -1 and count >= self.getMaxResults():
                break
            matchNames.append(searchResult.Name)
            sys.stderr.write("[%3d][%2d][%32s]\n" % (searchResult.Percent,searchResult.Age,searchResult.Name))
            count += 1


        sys.stderr.write("After Cut [%s] Results\n" % len(matchNames))
        if not self.getSkipVisit():
            for matchName in matchNames:
                matchProfile    =   MatchProfile()
                matchProfile.loadFromSession(session,matchName)
    
                for question in matchProfile.Questions:
                    if not self.__questions.hasQuestion(question.Id):
                        self.__questions.addQuestion(question.Id,question.Text,question.Answers)
                self.__questions.saveQuestions()
                fileName    =   "%s.ini" % matchProfile.Info["Name"]
                fullName    =   os.path.join(self.getExperimentPath(),fileName)
 
                matchProfile.saveProfile(fullName)
                self.saveMatch(matchProfile.Info["Name"],fullName) 

        sys.stderr.write("Finished Experiment\n")
