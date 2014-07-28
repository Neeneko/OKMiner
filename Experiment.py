import datetime
import os
import gc
import re
import sys
import csv
import ConfigParser
import logging
import shutil
import shlex
import json
import urllib
from SessionManager import SessionManager
from Profile import UserProfile,MatchProfile
from Search import GentationFilter


class   MinerExperiment(object):

    PROPERTIES  =   {
                        "UserName"      : None,
                        "MinMatch"      : "80",
                        "AgeRange"      : "10",
                        "AgeMin"        : None,
                        "AgeMax"        : None,
                        "Gentation"     : None,
                        "RatingSlices"  : None
                    }

    def __init__(self,experiment_name):
        self.__rootPath             =   os.path.dirname(sys.modules[__name__].__file__)
        self.__dataPath             =   os.path.join(os.path.dirname(sys.modules[__name__].__file__), "Data")
        self.__expPath              =   os.path.join(self.__dataPath,experiment_name)
        self.__searchPath           =   os.path.join(self.__expPath,"Searches")
        self.__profilePath          =   os.path.join(self.__expPath,"Profiles")
        self.__configFile           =   os.path.join(self.__expPath,"experiment.ini")
        self.__expName              =   experiment_name
        self.__config               =   ConfigParser.ConfigParser()
        self.__config.optionxform   =   str
 
    def init(self):
        logging.info("Initializing Experiment [%s]" % self.__expName)

        bigConfigPath   =   os.path.join(self.__rootPath,"Config","experiments.ini")
        if not os.path.exists(bigConfigPath):
            raise RuntimError,"Global experiment list not found"

        bigConfig       =   ConfigParser.ConfigParser()
        bigConfig.optionxform=str
        
        bigConfig.read(bigConfigPath)
        if not bigConfig.has_section(self.__expName):
            raise RuntimeError,"No such experiment [%s] in global list" % self.__expName       

        if not os.path.exists(self.__dataPath):
            logging.warn("Data path does not exist, creating")
            os.mkdir(self.__dataPath)

        if os.path.exists(self.__expPath):
            logging.warn("Old experiment directory exists, clearing")
            shutil.rmtree(self.__expPath)
        os.mkdir(self.__expPath)
        os.mkdir(self.__searchPath)
        os.mkdir(self.__profilePath)

        self.__config.add_section("Settings")
        self.__config.add_section("Locations")
        self.__config.add_section("User")
        self.__config.add_section("Timestamps")
        for k,v in MinerExperiment.PROPERTIES.iteritems():
            if bigConfig.has_option(self.__expName,k):
                self.__config.set("Settings",k,bigConfig.get(self.__expName,k))
            else:
                self.__config.set("Settings",k,v)

        SessionManager.doLogin(self.getUserName())

        self.__fillUserProfile()

        if bigConfig.has_option(self.__expName,"Locations"):
            parser = shlex.shlex(bigConfig.get(self.__expName,"Locations"))
            parser.whitespace += ','
            for location in parser:
                if location == "Anywhere":
                    self.__config.set("Locations",location,"%s,0" % self.__getLocation(location))
                else:
                    self.__config.set("Locations",location,"%s,25" % self.__getLocation(location))
        else:
            self.__config.set("Locations","Near me","%s,25" % self.__getLocation("Near me"))

        self.saveConfig()

    def getSearchPath(self):
        return self.__searchPath

    def getProfilePath(self):
        return self.__profilePath

    def saveConfig(self):
       with open(self.__configFile,'wb') as configFile:
            self.__config.write(configFile)

    def saveTimestamp(self,label):
        self.__config.set("Timestamps",label,str(datetime.datetime.now()))
        self.saveConfig()

    def loadConfig(self,config_name):
        self.__config.read(config_name)

    def getUserName(self):
        return self.__config.get("Settings","UserName")

    def getRatingSlices(self):
        if self.__config.get("Settings","RatingSlices") == "None" or self.__config.get("Settings","RatingSlices") is None:
            return None
        splitList = re.split(",",self.__config.get("Settings","RatingSlices"))
        count   =   int(splitList[0])

        if count == 0:
            return None

        if len(splitList) == 1:
            rv = []
            for rating in range(count):
                rlow   =   rating*(10000/count)
                rhigh   =   (rating+1)*(10000/count)
                rv.append( (rlow,rhigh) )
            return rv
        elif splitList[1] == "Interlaced":
            rv = []
            sliceSize   =   10000/count
            for rating in range(count):
                rlow   =   rating*(sliceSize)
                rhigh   =   (rating+1)*(sliceSize)
                rv.append( (rlow,rhigh) )
                rlow   =   rating*(sliceSize)+sliceSize/2
                rhigh   =  min((rating+1)*(sliceSize)+sliceSize/2,10000)
                rv.append( (rlow,rhigh) )
            return rv
        else:
            raise RuntimeError

    def getAgeRange(self):
        try:
            ageMin      =   self.__config.getint("Settings","AgeMin")
        except TypeError:
            ageMin      =   None
        try:
            ageMax      =   self.__config.getint("Settings","AgeMax")
        except TypeError:
            ageMax      =   None

        try:
            ageRange    =   self.__config.getint("Settings","AgeRange")
        except TypeError:
            ageRange    =   0

        userAge     =   self.__config.getint("User","Age")

        ageLow      =   userAge-ageRange
        ageHigh     =   userAge+ageRange

        if ageMin is not None:
            ageLow  =   min(ageLow,ageMin)

        if ageMax is not None:
            ageHigh =   max(ageHigh,ageMax)

        return range(ageLow,ageHigh+1)

    def getLocationRange(self):
        return [ re.split(',',x) for (_,x) in self.__config.items("Locations")]

    def getGentationRange(self):
        gentation   =   GentationFilter.getGentation(self.__config.get("Settings","Gentation"))
        rv          =   []
        for i in range(6):
            tmp = 1<<i
            if gentation&tmp != 0:
                rv.append(gentation&tmp)
        return rv

    def __getLocation(self,name):
        payload =   {
                        "okc_api"   :   1,
                        "func"      :   "query",
                        "query"     :   name
                    }
        payloadStr  =   urllib.urlencode(payload)

        page = SessionManager.getSession().get("http://www.okcupid.com/locquery?%s" % payloadStr)
        data    =   json.loads(page.text)
        return data["locid"]

    def __fillUserProfile(self):
        payload =   {
                        "okc_api"   :   1
                    }
        payloadStr  =   urllib.urlencode(payload)

        page = SessionManager.getSession().get("http://www.okcupid.com/profile/%s?%s" % (self.getUserName(),payloadStr))
        data    =   json.loads(page.text)


        self.__config.set("User","Age","%s" % data["age"])

class   _MinerExperiment(object):

    PROPERTIES  =   {
                        "UserName"      : None,
                        "MaxResult"     : None,
                        "MinMatch"      : "80",
                        "Radius"        : "50",
                        "AgeRange"      : "10",
                        "AgeMin"        : None,
                        "AgeMax"        : None,
                        "SearchTypes"   : "Match",
                        "Gentation"     : None
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
        self.__userProfile  =   UserProfile()

    def getGentation(self):
        return self.__config.get("Settings","Gentation")

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

    def getSearchTypes(self):
        try:
            rv = re.split(",",self.__config.get("Settings","SearchTypes"))
        except:
            rv = ["Match"]
        return rv

    def createExperiment(self,properties):
        expDir = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        self.__expPath      =   os.path.join(self.__dataPath,expDir)
        self.__configName   =   os.path.join(self.__expPath,"experiment.ini")

        os.mkdir(self.__expPath)
        self.__config.add_section("Settings")
        self.__config.add_section("Searches")
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
        userName,userFile   =   self.getProfiles("User")[0]

        self.__userProfile = UserProfile()
        self.__userProfile.loadFromConfig(userFile)

    def getUserProfile(self):
        return self.__userProfile

    def getAgeRange(self):
        baseAge         = int(self.__userProfile.Info["Age"])
        
        if self.__config.get("Settings","AgeRange") is None:
            ageHigh =   baseAge
            ageLow  =   baseAge
        else:
            ageHigh =   baseAge+int(self.__config.get("Settings","AgeRange"))
            ageLow  =   baseAge-int(self.__config.get("Settings","AgeRange"))
        try:
            if self.__config.get("Settings","AgeMin") is not None:
                ageLow  =   int(self.__config.get("Settings","AgeMin"))
        except:
            pass

        try:
            if self.__config.get("Settings","AgeMax") is not None:
                ageHigh =   int(self.__config.get("Settings","AgeMax"))
        except:
            pass


        return (ageLow,ageHigh)

    def getGentation(self):
        gentation = self.__config.get("Settings","Gentation") 
        if gentation is not None and gentation != "None":
            return gentation
        else:
            raise RuntimeError,"No Longer Supported, must define Gentation"
            gender      =   self.__userProfile.Info["Gender"]
            orientation =   self.__userProfile.Info["Orientation"]
            return GentationFilter.genGentation(gender,orientation)

    def getUserName(self):
        return self.__config.get("Settings","UserName")

    def getExperimentPath(self):
        return self.__expPath
        
    def saveSearch(self,match_type,age,names):
        self.__config.set("Searches","%s,%s" % (match_type,age),"%s" % str(names)) 
        self.saveConfig()

    def getSearches(self,match_type):
        rv = {}
        for searchName,searchResults in self.__config.items("Searches"):
            splitList = re.split(',',searchName)
            if splitList[0] == match_type:
                rv[int(splitList[1])] = eval(searchResults)
        return rv 

    def saveProfile(self,match_type,match_name,match_file_name):
        if match_type not in self.__config.sections():
            self.__config.add_section(match_type)
        self.__config.set(match_type,match_name,match_file_name)
        self.saveConfig()

    def getProfiles(self,match_type):
        return self.__config.items(match_type)

    def doExperiment(self):
        sys.stderr.write("Starting Experiment against profile [%s]\n" % self.getUserName())
        profileManager  =   ProfileManager()
        session         =   profileManager.doLogin(self.getUserName())


        self.__userProfile.loadFromSession(session,self.getUserName(),True)
        fileName        =   "%s.ini" %  self.__userProfile.Info["Name"] 
        fullName        =   os.path.join(self.getExperimentPath(),fileName)
        self.__userProfile.saveProfile(fullName)
        self.saveProfile("User",self.__userProfile.Info["Name"],fullName)

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

        for searchType in self.getSearchTypes():
            matches = []
            for i in range(ageLow,ageHigh+1):
                gc.collect()
                url = genSearchURL(MatchOrder(searchType.upper()),AgeFilter(i,i),LastOnFilter(LastOnFilter.WEEK),LocationIdFilter(locationId,radius),GentationFilter(self.getGentation()),PhotoFilter(False),StatusFilter(StatusFilter.ANY))
                sys.stderr.write("[%s][%s] Search [%s]\n" % (searchType,i,url))
                results         =   doSearch(session,url)
                self.saveSearch(searchType,i,results)
                saved           =   0                
                for result in results:
                    sys.stderr.write("[%s][%s] Loading [%s]\n" % (searchType,i,result))
                    matchProfile    =   MatchProfile()
                    if not matchProfile.loadFromSession(session,result):
                        self.saveProfile("Error",result,"%s" % str(matchProfile.Error))
                        continue
                        

                    sys.stderr.write("[%s][%s] Answers [%s]\n" % (searchType,i,len(matchProfile.Answers)))
                    percent = matchProfile.Percentages[searchType]
                    sys.stderr.write("[%s][%s] Filtering - [%s]\n" % (searchType,i,percent))

                    if self.getMinMatch() != -1 and percent < self.getMinMatch():
                        break

                    if self.getMaxResults() != -1:
                        if len(matches) < self.getMaxResults():
                            #sys.stderr.write("\tAdding\n")
                            matches.append(matchProfile)
                        elif matches[-1].Percentages[searchType] < percent:
                            #sys.stderr.write("\tReplacing\n")
                            matches[-1] = matchProfile
                        else:
                            #sys.stderr.write("\tSkipping\n")
                            break

                        def keyFxn(value):
                            return value.Percentages[searchType]

                        matches = sorted( matches,key=keyFxn,reverse=True)
                    else:
                        matches.append(matchProfile)
                        #sys.stderr.write("\tSorted - %s\n" % [ x.Percentages[searchType] for x in matches[searchType] ])
                    saved += 1
                sys.stderr.write("Slice [%s] Type [%s] Results [%s] Saved [%s] Cumulative [%s]\n" % (i,searchType,len(results),saved,len(matches)))

            for match in matches:
                sys.stderr.write("Saving [%s]\n" % match.Info["Name"])

                fileName    =   "%s.ini" % match.Info["Name"]
                fullName    =   os.path.join(self.getExperimentPath(),fileName)
                    
                match.saveProfile(fullName)
                self.saveProfile(searchType,match.Info["Name"],fullName)
        sys.stderr.write("Finished Experiment\n")
