import datetime
import os
import gc
import sys
import ConfigParser

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
                        "SkipVisit"     : False,
                        "IncludeEnemy"  : False,
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

    def getSkipVisit(self):
        return bool(self.__config.get("Settings","SkipVisit"))

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

    def getIncludeEnemy(self):
        try:
            rv = bool(self.__config.get("Settings","IncludeEnemy"))
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
        """
        self.__config.add_section("Matches")
        self.__config.add_section("Enemies")
        """
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


        self.__userProfile.loadFromSession(session,self.getUserName())
        fileName        =   "%s.ini" %  self.__userProfile.Info["Name"] 
        fullName        =   os.path.join(self.getExperimentPath(),fileName)
        self.__userProfile.saveProfile(fullName)
        self.saveProfile("User",self.__userProfile.Info["Name"],fullName)

        gender          = self.__userProfile.Info["Gender"]
        orientation     = self.__userProfile.Info["Orientation"]
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
                    matchProfile.loadFromSession(session,result)

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
