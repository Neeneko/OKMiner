import datetime
import os
import sys
import ConfigParser


from Profile import UserProfile,MatchProfile
from Search import *

def doExperiment(session,experiment,questions):
    userProfile     =   UserProfile()
    userProfile.loadFromSession(session,experiment.getUserName())
    fileName        =   "%s.ini" %  userProfile.Info["Name"] 
    fullName        =   os.path.join(experiment.getExperimentPath(),fileName)
 
    userProfile.saveProfile(fullName)
    for question in userProfile.Questions:
        if not questions.hasQuestion(question.Id):
            questions.addQuestion(question.Id,question.Text,question.Answers)
    questions.saveQuestions()
    url = genSearchURL(AgeFilter(36,36),LastOnFilter(LastOnFilter.WEEK),ZipCodeFilter(19053,50),GentationFilter("girls who like guys"))
    experiment.saveSearchURL(url)
    searchResults   =   doSearch(session,url)

    count           =   0
    matchNames      =   []
    for (matchName,matchPercent) in searchResults:
        if matchPercent < experiment.getMinMatch():
            continue
        if count >= experiment.getMaxResults():
            break
        matchNames.append(matchName)
        sys.stderr.write("[%3d][%32s]\n" % (matchPercent,matchName))
        count += 1

    #return
    #matchNames   =   [ "VeganPhD" ]
    #matchNames   =   [ "VeganPhD", "ItsMyBeat", "KimikoCat", "Sushibitch", "TheAnomie", "wintermysecret", "GLilyDances" ]
    for matchName in matchNames:
        matchProfile    =   MatchProfile()
        matchProfile.loadFromSession(session,matchName)
    
        for question in matchProfile.Questions:
            if not questions.hasQuestion(question.Id):
                questions.addQuestion(question.Id,question.Text,question.Answers)
        questions.saveQuestions()
        fileName    =   "%s.ini" % matchProfile.Info["Name"]
        fullName    =   os.path.join(experiment.getExperimentPath(),fileName)
 
        matchProfile.saveProfile(fullName)
        experiment.saveMatch(matchProfile.Info["Name"],fullName) 

class   MinerExperiment(object):

    def __init__(self):
        self.__dataPath     =   os.path.join(os.path.dirname(sys.modules[__name__].__file__), "Data")
        self.__config       =   ConfigParser.ConfigParser()
        self.__config.optionxform=str
        
    def getMaxResults(self):
        return int(self.__config.get("Settings","MaxResults"))

    def getMinMatch(self):
        return int(self.__config.get("Settings","MinMatch"))

    def createExperiment(self,user_name):
        """
        @TODO - experiment files will come later
        """
        #self.__userName     =   user_name
        if not os.path.exists(self.__dataPath):
            sys.stderr.write("Data path does not exist, creating\n")
            os.mkdir(self.__dataPath)
        expDir = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        self.__expPath      =   os.path.join(self.__dataPath,expDir)
        self.__configName   =   os.path.join(self.__expPath,"experiment.ini")

        os.mkdir(self.__expPath)
        self.__config.add_section("Settings")
        self.__config.add_section("Searches")
        self.__config.add_section("Matches")
        self.__config.set("Settings","UserName",user_name) 
        self.__config.set("Settings","MaxResults","5") 
        self.__config.set("Settings","MinMatch","75")
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
        #return self.__userName

    def getExperimentPath(self):
        return self.__expPath

    """
    def saveProfile(self,profile):
        if profile.Info["Name"] == self.getUserName():
            fileName    =   "%s.profile.ini" %  profile.Info["Name"] 
        else:
            fileName    =   "%s.match.ini" % profile.Info["Name"]
        fullName    =   os.path.join(self.__expPath,fileName)
        parser       =   ConfigParser.ConfigParser()
        parser.optionxform=str

        parser.add_section("Info")
        for k,v in profile.Info.iteritems():
            parser.set("Info",k,v)

        parser.add_section("Details")
        for k,v in profile.Details.iteritems():
            parser.set("Details",k,v)

        parser.add_section("LookingFor")
        for k,v in profile.LookingFor.iteritems():
            parser.set("LookingFor",k,v)

        parser.add_section("Essays")
        for idx in range(len(profile.Essays)):
            parser.set("Essays","Essay_%02d" % idx,profile.Essays[idx])

        with open(fullName,'wb') as fp:
            parser.write(fp)
    """
        
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
