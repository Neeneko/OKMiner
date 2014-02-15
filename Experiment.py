import datetime
import os
import sys
import ConfigParser


from Profile import UserProfile

def doExperiment(session,experiment,questions):
    userProfile     =   UserProfile(session,experiment.getUserName())
    if userProfile.Info["Name"] == experiment.getUserName():
        fileName    =   "%s.profile.ini" %  userProfile.Info["Name"] 
    else:
        fileName    =   "%s.match.ini" % userProfile.Info["Name"]
    fullName    =   os.path.join(experiment.getExperimentPath(),fileName)
 
    userProfile.saveProfile(fullName)
    for question in userProfile.Questions:
        #sys.stderr.write("Question [%s]\n" % quesiton.Id)
        if not questions.hasQuestion(question.Id):
            questions.addQuestion(question.Id,question.Text,question.Answers)
    questions.saveQuestions()

class   MinerExperiment(object):

    def __init__(self):
        self.__dataPath     =   os.path.join(os.path.dirname(sys.modules[__name__].__file__), "Data")
        self.__config       =   ConfigParser.ConfigParser()
        self.__config.optionxform=str
     

    def loadExperiment(self,user_name):
        """
        @TODO - experiment files will come later
        """
        self.__userName     =   user_name
        if not os.path.exists(self.__dataPath):
            sys.stderr.write("Data path does not exist, creating\n")
            os.mkdir(self.__dataPath)
        expDir = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        self.__expPath      =   os.path.join(self.__dataPath,expDir)
        self.__configName   =   os.path.join(self.__expPath,"experiment.ini")

        os.mkdir(self.__expPath)
        self.__config.add_section("Settings")
        self.__config.set("Settings","Username",user_name) 

        self.saveConfig()

    def saveConfig(self):
       with open(self.__configName,'wb') as configFile:
            self.__config.write(configFile)

    def getUserName(self):
        return self.__userName

    def getExperimentPath(self):
        return self.__expPath

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

        


        


