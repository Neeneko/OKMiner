import ConfigParser
import os
import sys
import base64

class   MinerSession(object):

    def __init__(self):
        self.__dataPath     =   os.path.join(os.path.dirname(sys.modules[__name__].__file__), "Data")
        #self.__dataPath     =   os.path.join(OKMiner.__path__[0], "Data")
        self.__config       =   ConfigParser.RawConfigParser()
        self.__configName   =   os.path.join(self.__dataPath,"config.ini")
        self.__session      =   None

    def saveConfig(self):
        with open(self.__configName,'wb') as configFile:
            self.__config.write(configFile)

    def loadConfig(self):
        if not os.path.exists(self.__dataPath):
            sys.stderr.write("Data path does not exist, creating\n")
            os.mkdir(self.__dataPath)
        if not os.path.exists(self.__configName):
            sys.stderr.write("Data file does not exist, creating\n")
            self.__config.add_section("Profiles")
            self.saveConfig()

        self.__config.read(self.__configName)

    def getProfileNames(self):
        return [ x for (x,_) in self.__config.items("Profiles") ]

    def addProfile(self,user_name,pass_word):
        self.__config.set("Profiles",user_name,base64.b64encode(pass_word))

    def updateProfile(self,user_name,pass_word):
        self.addProfile(user_name,pass_word)

    def delProfile(self,user_name):
        self.__config.remove_option("Profiles",user_name)

    def getPassword(self,user_name):
        return base64.b64decode(self.__config.get("Profiles",user_name))

    def getSession(self):
        return self.__session

    def setSession(self,session):
        self.__session = session