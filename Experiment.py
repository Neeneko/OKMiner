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
                        "SkipVisit"     : False,
                        "IncludeEnemy"  : False
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

    def getIncludeEnemy(self):
        try:
            rv = bool(self.__config.get("Settings","IncludeEnemy"))
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
        self.__config.add_section("Enemies")

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

    def saveEnemy(self,match_name,match_file_name):
        self.__config.set("Enemies",match_name,match_file_name)
        self.saveConfig()

    def getEnemiesCount(self):
        return len(self.__config.options("Enemies"))
 
    def getEnemies(self):
        return self.__config.items("Enemies")



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


        matchResults    =   []

        def CountType(results,type):
            rv = 0
            for result in results:
                if result.Type == type:
                    rv+=1
            return rv

        def GetTypes(results):
            rv = []
            for result in results:
                if result.Type not in rv:
                    rv.append(result.Type)
            return rv

        for i in range(ageLow,ageHigh+1):
            url = genSearchURL(MatchOrder("MATCH"),AgeFilter(i,i),LastOnFilter(LastOnFilter.WEEK),LocationIdFilter(locationId,radius),TargetedGentationFilter(gender,orientation))

            sys.stderr.write("Search [%s]\n" % url)
            self.saveSearchURL(url)
            oneSearch       =   doSearch(session,url,self.getMinMatch())
            matchResults    +=  oneSearch
            sys.stderr.write("Slice [%s] Match [%s] Cumulative [%s]\n" % (i,len(oneSearch),len(matchResults)))

            if self.getIncludeEnemy():
                url = genSearchURL(MatchOrder("ENEMY"),AgeFilter(i,i),LastOnFilter(LastOnFilter.WEEK),LocationIdFilter(locationId,radius),TargetedGentationFilter(gender,orientation))
                sys.stderr.write("Search [%s]\n" % url)
                self.saveSearchURL(url)

                oneSearch       =   doSearch(session,url,self.getMinMatch())
                matchResults    +=  oneSearch
                sys.stderr.write("Slice [%s] Enemy [%s] Cumulative [%s]\n" % (i,len(oneSearch),len(matchResults)))

        tempString  =   "Before Cut "
        for typeString in GetTypes(matchResults):
            tempString += "%s [%s] " % (typeString,CountType(matchResults,typeString))
        tempString  +=  "Total [%s]\n" % len(matchResults)
        sys.stderr.write(tempString)

        count           =   0
        filteredResults =   []
        for result in sorted(matchResults):
            if self.getMinMatch() != -1 and result.Percent < self.getMinMatch():
                continue
            if self.getMaxResults() != -1 and count >= self.getMaxResults():
                break
            filteredResults.append(result)
            sys.stderr.write("[%3d][%2d][%s][%32s]\n" % (result.Percent,result.Age,result.Type,result.Name))
            count += 1


        tempString  =   "After Cut "
        for typeString in GetTypes(filteredResults):
            tempString += "%s [%s] " % (typeString,CountType(filteredResults,typeString))
        tempString  +=  "Total [%s]\n" % len(filteredResults)
        sys.stderr.write(tempString)

        if not self.getSkipVisit():
            for result in filteredResults:
                matchProfile    =   MatchProfile()
                matchProfile.loadFromSession(session,result.Name)
    
                for question in matchProfile.Questions:
                    if not self.__questions.hasQuestion(question.Id):
                        self.__questions.addQuestion(question.Id,question.Text,question.Answers)
                self.__questions.saveQuestions()
                fileName    =   "%s.ini" % matchProfile.Info["Name"]
                fullName    =   os.path.join(self.getExperimentPath(),fileName)
 
                matchProfile.saveProfile(fullName)
                if result.Type == "Enemy":
                    self.saveEnemy(matchProfile.Info["Name"],fullName)
                elif result.Type == "Match":
                    self.saveMatch(matchProfile.Info["Name"],fullName) 
                else:
                    raise RuntimeError,"What is a [%s] match type?\n" % result.Type

        sys.stderr.write("Finished Experiment\n")
