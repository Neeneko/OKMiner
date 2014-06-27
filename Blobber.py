import os
import logging
import optparse
import sqlite3
import glob
import json
import ConfigParser
import re
from lxml import html
from Search import GentationFilter

class ExperimentDb(object):

    SEX_FEMALE          =   "Female"
    SEX_MALE            =   "Male"

    ORIENTATION_GAY     =   "Gay"
    ORIENTATION_BI      =   "Bi"
    ORIENTATION_STRAIT  =   "Strait"


    CONTACT_FIELDS      =   {
                                "contacts_this_week"    :   "ContactsWeek",
                                "reply_perc"            :   "ReplyPercent",
                                "recent_contacts"       :   "ContactsRecent",
                                "recent_replies"        :   "RepliesRecent",
                            }

    INFO_FIELDS         =   {
                                "drinker"               :   "Drinks",
                                "cats"                  :   "Cats",
                                "bodytype"              :   "Body",
                                "drugs"                 :   "Drugs",
                                "dogs"                  :   "Dogs",
                                "sign"                  :   "Sign",
                                "sign_status"           :   "SignStatus",
                                "smoker"                :   "Smoker",
                                "diet"                  :   "Diet",
                                "religion"              :   "Religion",
                                "education"             :   "Education"
                            }

    SEARCH_FIELDS       =   {
                                "age_min"               :   "AgeMin",
                                "age_max"               :   "AgeMax",
                                "gentation"             :   "Gentation",
                                "only_singles"          :   "Singles",
                                "only_photos"           :   "Photos"
                            }

    LOOKING_FOR_FIELDS  =   {
                                "New friends"           :   "Friends",
                                "Long-term dating"      :   "LongTerm",
                                "Short-term dating"     :   "ShortTerm",
                                "Casual sex"            :   "CasualSex"

                            }

    def __init__(self,file_name):
        self.__db           =   sqlite3.connect(file_name,detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.__db.commit()
        self.__db.close()

    def getCursor(self):
        return self.__db.cursor()

    #-------------------------------------------------------------------------------------------------- 
    def createTables(self):
        cursor      =   self.__db.cursor()
        cursor.execute("CREATE TABLE Locations (LocationId PRIMARY KEY, Latitude REAL, Longitude REAL, City TEXT, State TEXT, Country TEXT)")
        cursor.execute("CREATE TABLE Users (UserId PRIMARY KEY, LocationId INT, Name TEXT, Age INT, Sex INT, Orientation INT, Match INT, JoinDate DATE, CrawlDate DATE)")
        cursor.execute("CREATE TABLE Experiment (Parameter TEXT,Value TEXT)")
        cursor.execute("CREATE TABLE Sample (Parameter TEXT,Value TEXT)")
        cursor.execute("CREATE TABLE SampleUsers (UserId PRIMARY KEY)")
        cursor.execute("CREATE TABLE Searches (SearchId PRIMARY KEY,Age INT,Location INT, Gentation INT, Rating TEXT)")
        cursor.execute("CREATE TABLE SearchToUser (SearchId INT, UserId INT)")

        cString =   "CREATE TABLE Contacts (UserId PRIMARY KEY"
        keys    =   sorted(ExperimentDb.CONTACT_FIELDS.keys())
        for idx in range(len(keys)):
            cString += ",%s INT" % ExperimentDb.CONTACT_FIELDS[keys[idx]]
        cString +=  ")"
        cursor.execute(cString)
 
        cString =   "CREATE TABLE UserInfos (UserId PRIMARY KEY"
        keys    =   sorted(ExperimentDb.INFO_FIELDS.keys())
        for idx in range(len(keys)):
            cString += ",%s INT" % ExperimentDb.INFO_FIELDS[keys[idx]]
        cString +=  ",Height REAL,RelationshipStatus TEXT,RelationshipType TEXT"
        cString +=  ")"
        cursor.execute(cString)

        cursor.execute("CREATE TABLE UserEthnicities (UserId INT,Ethnicity TEXT)")        
        cursor.execute("CREATE TABLE UserLanguages (UserId INT,Language TEXT,Degree TEXT)")        
 
        cString =   "CREATE TABLE UserLookingFor (UserId PRIMARY KEY"
        keys    =   sorted(ExperimentDb.SEARCH_FIELDS.keys())
        for idx in range(len(keys)):
            cString += ",%s INT" % ExperimentDb.SEARCH_FIELDS[keys[idx]]
        keys    =   sorted(ExperimentDb.LOOKING_FOR_FIELDS.keys())
        for idx in range(len(keys)):
            cString += ",%s BOOLEAN" % ExperimentDb.LOOKING_FOR_FIELDS[keys[idx]]
        cString +=  ")"
        cursor.execute(cString)
        #----------------------------------------------------------------------------------------------
        cursor.execute("CREATE TABLE Gentation (GentationId INT, GentationText TEXT)")

        for k,v in GentationFilter.CONSTANTS.iteritems():
            cursor.execute("INSERT INTO Gentation VALUES (?,?)",[v,k])

     
    def clear(self):
        cursor      =   self.__db.cursor()
        cursor.execute("DROP TABLE IF EXISTS Experiment")
        cursor.execute("DROP TABLE IF EXISTS Locations")
        cursor.execute("DROP TABLE IF EXISTS Users")
        cursor.execute("DROP TABLE IF EXISTS Contacts")
        cursor.execute("DROP TABLE IF EXISTS Sample")
        cursor.execute("DROP TABLE IF EXISTS SampleUsers")
        cursor.execute("DROP TABLE IF EXISTS Searches")
        cursor.execute("DROP TABLE IF EXISTS SearchToUser")
        cursor.execute("DROP TABLE IF EXISTS UserInfos")
        cursor.execute("DROP TABLE IF EXISTS UserEthnicities")
        cursor.execute("DROP TABLE IF EXISTS UserLanguages")
        cursor.execute("DROP TABLE IF EXISTS UserLookingFor")
        cursor.execute("DROP TABLE IF EXISTS Gentation")
    #-------------------------------------------------------------------------------------------------- 
    def loadExperiment(self,file_name,experiment):
        cursor              =   self.__db.cursor()
        config              =   ConfigParser.ConfigParser()
        config.optionxform  =   str
        config.read(file_name)
        for k,v in config.items("Settings"):
            cursor.execute("INSERT INTO Experiment VALUES (?,?)" , (k,v))
        cursor.execute("INSERT INTO Experiment VALUES (?,?)" , ("Experiment",experiment))

        if config.has_section("Sample"):
            for k,v in config.items("Sample"):
                cursor.execute("INSERT INTO Sample VALUES (?,?)" , (k,v))
 
    def loadProfile(self,file_name):
        logging.info("Loading [%s]" % file_name)
        cursor      =   self.__db.cursor()

        with open(file_name) as fp:
            data        =   json.load(fp)

        userId      =   data["userid"]
        cursor.execute("INSERT INTO SampleUsers VALUES (?)",[userId])

        heightStr   =   data["skinny"]["height"]
        if len(heightStr) != 0:
            hi          =   heightStr.find(")")
            li          =   heightStr.find("(")
            height      =   float(heightStr[li+1:hi-1])
        else:
            height      =   None

        root,_      =   os.path.splitext(file_name)
        fileName    =   "%s.html" % root
        tree        =   html.parse(fileName)
        rStatus     =   tree.xpath('//dd[@id="ajax_status"]/text()')[0].strip()
        rType       =   tree.xpath('//dd[@id="ajax_monogamous"]/text()')[0].strip()

        cString =   "INSERT INTO UserInfos VALUES (?"
        keys    =   sorted(ExperimentDb.INFO_FIELDS.keys())
        values  =   [userId]
        for idx in range(len(keys)):
            cString += ",?"
            if keys[idx] in data["skinny"]:
                values.append(data["skinny"][keys[idx]])
            else:
                values.append(None)
        cString += ",?,?,?"
        values  +=  [height,rStatus,rType]
        cString +=  ")"
        cursor.execute(cString,values)

        for value in data["skinny"]["ethnicities"]:
            cursor.execute("INSERT INTO UserEthnicities VALUES (?,?)",[userId,value])
            
        for value in data["skinny"]["languages"]:
            splitList   =    re.split(' ',value)
            if len(splitList) == 1:
                lang    =   splitList[0]
                skill   =   None
            elif len(splitList) == 2:
                lang    =   splitList[0]
                skill   =   splitList[1][1:-1]

            cursor.execute("INSERT INTO UserLanguages VALUES (?,?,?)",[userId,lang,skill])
 
        cString =   "INSERT INTO UserLookingFor VALUES (?"
        values  =   [userId]
        keys    =   sorted(ExperimentDb.SEARCH_FIELDS.keys())
        for idx in range(len(keys)):
            cString += ",?"
            values.append(data["searchprefs"][keys[idx]])
        keys    =   sorted(ExperimentDb.LOOKING_FOR_FIELDS.keys())
        for idx in range(len(keys)):
            cString += ",?"
            values.append( keys[idx] in data["skinny"]["lookingfor"] )
        cString +=  ")"
        cursor.execute(cString,values)


    def loadSearch(self,file_name):
        logging.info("Loading [%s]" % file_name)
        cursor      =   self.__db.cursor()

        with open(file_name) as fp:
            data        =   json.load(fp)
            baseName    =   os.path.basename(file_name)
            searchParam =   baseName[:baseName.rfind(".p")]
            searchId    =   hash(searchParam)
            cursor.execute("SELECT COUNT(*) FROM Searches WHERE SearchId=?",[searchId])
            if cursor.fetchone()[0] == 0:
                splitList   =   re.split('\.',searchParam)
                age         =   int(splitList[0])
                location    =   int(splitList[1])
                gentation   =   int(splitList[2])
                rating      =   splitList[3]
                cursor.execute("INSERT INTO Searches VALUES (?,?,?,?,?)", [searchId,age,location,gentation,rating])
           
            crawlDate   =   data["cache_timekey"]
            for result in data["amateur_results"]:
                locId       =   result["location_detail"]["locid"]
                userId      =   result["userid"]
                cursor.execute("INSERT INTO SearchToUser VALUES (?,?)", [searchId,userId])
                cursor.execute("SELECT COUNT(*) FROM Users WHERE UserId=?",[userId])
                row     =   cursor.fetchone()
                if row[0] != 0:
                    continue

                userName    =   result["username"]
                userAge     =   result["age"]
                if result["gender"] == "f":
                    userSex  = ExperimentDb.SEX_FEMALE
                elif result["gender"] == "m":  
                    userSex  = ExperimentDb.SEX_MALE
                else:
                    raise RuntimeError,"Unexepcted gender [%s] in results" % result["gender"]
                #TODO - we need to double check this
                if result["orientation_code"] == 1:
                    userOrientation = ExperimentDb.ORIENTATION_STRAIT
                elif result["orientation_code"] == 2:
                    userOrientation = ExperimentDb.ORIENTATION_GAY
                elif result["orientation_code"] == 3:
                    userOrientation = ExperimentDb.ORIENTATION_BI
                else:
                    raise RuntimeError,"Unexepcted orientation_code [%s] in results" % result["orientation_code"]
                
                userJoin    =   result["join_date"]
                userMatch   =   result["match_percentage"]  

                cursor.execute("INSERT INTO Users VALUES (?,?,?,?,?,?,?,?,?)", [userId,locId,userName,userAge,userSex,userOrientation,userMatch,userJoin,crawlDate])
                #------------------------------------------------------------------------
                cString =   "INSERT INTO Contacts VALUES (?"
                keys    =   sorted(ExperimentDb.CONTACT_FIELDS.keys())
                values  =   [userId]
                for idx in range(len(keys)):
                    cString += ",?"
                    values.append(result[keys[idx]])
                cString +=  ")"
                cursor.execute(cString,values)
                #------------------------------------------------------------------------
                cursor.execute("SELECT COUNT(*) FROM Locations WHERE LocationId=?",[locId])
                row     =   cursor.fetchone()
                if row[0] != 0:
                    continue

                lat     =   result["location_detail"]["position"]["latitude"]
                lon     =   result["location_detail"]["position"]["longitude"]
                city    =   result["location_detail"]["location"]["city_name"]
                state   =   result["location_detail"]["location"]["state_name"]
                country =   result["location_detail"]["location"]["country_name"]
                cursor.execute("INSERT INTO Locations VALUES (?,?,?,?,?,?)",[locId,lat,lon,city,state,country])
    #-------------------------------------------------------------------------------------------------- 
    def getExperimentName(self):
        cursor      =   self.__db.cursor()
        cursor.execute("SELECT Value FROM Experiment WHERE Parameter=?",["Experiment"])
        row     =   cursor.fetchone()
        return row[0]

    def GetUserCount(self,**kwargs):
        rows        =   self.GetUsers("COUNT(*)",**kwargs)
        return int(rows[0][0])

    def GetFieldSum(self,field,**kwargs):
        rows        =   self.GetUsers("SUM(%s)" % field,**kwargs)
        return int(rows[0][0])

    def GetSampleUserCount(self,**kwargs):
        return len(self.GetUsers("SampleUsers.UserId",**kwargs))

    def GetUsers(self,*args,**kwargs):
        return self.GetRecords("User",*args,**kwargs)

    def GetUserInfos(self,*args,**kwargs):
        return self.GetRecords("UserInfo",*args,**kwargs)

    def GetLocations(self,*args,**kwargs):
        return self.GetRecords("Location",*args,**kwargs)

    def GetRecords(self,base,*args,**kwargs):
        cursor      =   self.__db.cursor()
        sString     =   "%ss" % base
        cString     =   ""
        filters     =   []
        for idx in range(len(args)):
            if idx != 0:
                cString += ","
            if '.' in args[idx]:

                splitList = re.split("\.",args[idx])
                table = splitList[0]

                if table not in sString:
                    sString += ",%s" % table
                    filters.append("%ss.%sId = %s.%sId" % (base,base,table,base))
                cString += args[idx]
            else:
                cString += args[idx]
                
        if "activeInDays" in kwargs:
            filters.append("CrawlDate-LastActivity < %d" % kwargs["activeInDays"])

        if "filterEqField" in kwargs:
            for idx in range(len(kwargs["filterEqField"])/2):
                filters.append("%s=\"%s\"" % (kwargs["filterEqField"][idx*2],kwargs["filterEqField"][1+idx*2]))

        if "filterGtField" in kwargs:
            filters.append("%s>\"%s\"" % kwargs["filterGtField"])

        if len(filters) != 0:
            fString =   "WHERE "
        else:
            fString =   ""

        for idx in range(len(filters)):
            if idx != 0:
                fString +=  " AND "
            fString     +=  filters[idx]

        eString     =   "SELECT %s FROM %s %s" % (cString,sString,fString)
        logging.info("[%s]" % eString)
        cursor.execute(eString)
        return cursor.fetchall()

    def GetRaw(self,query):
        cursor      =   self.__db.cursor()
        logging.info("[%s]" % query)
        cursor.execute(query)
        return cursor.fetchall()


    def GetUsersYoungerThen(self,seconds):
        cursor = self.__db.cursor()
        cursor.execute("SELECT UserId FROM Users WHERE CrawlDate-JoinDate < %d" % seconds)
        return cursor.fetchall()

    def GetUsersOlderThen(self,seconds):
        cursor = self.__db.cursor()
        cursor.execute("SELECT UserId FROM Users WHERE CrawlDate-JoinDate > %d" % seconds)
        return cursor.fetchall()

    def GetUsersJoinRange(self,older,younger):
        cursor = self.__db.cursor()
        cursor.execute("SELECT UserId FROM Users WHERE CrawlDate-JoinDate > %d AND CrawlDate-JoinDate < %d " % (older,younger))
        return cursor.fetchall()



def LoadSavedBlob(file_name):
    return ExperimentDb(file_name)

def CreateMemoryOnlyBlob(experiment):
    return CreateLiveBlob(":memory:",experiment)

def CreateLiveBlob(file_name,experiment):
    searchPath  =   os.path.join("Data",experiment,"Searches")
    if file_name == ":memory:":
        dbName  =   file_name
    else:
        dbName  =   os.path.join("Data",experiment,file_name)
    db  =   ExperimentDb(dbName)
    db.clear()
    db.createTables()
    for fileName in glob.glob(os.path.join("Data",experiment,"Searches","*.json")):
        db.loadSearch(fileName)
    for fileName in glob.glob(os.path.join("Data",experiment,"Profiles","*.json")):
        db.loadProfile(fileName)
    db.loadExperiment(os.path.join("Data",experiment,"experiment.ini"),experiment)
    return db

if __name__ == "__main__":
    usage       =   "usage: %prog [options] experiment"
    description =   "Process an experiment into a database"
    parser = optparse.OptionParser(usage=usage,description=description)

    options, args = parser.parse_args()

    if len(args) != 1:
        sys.stderr.write("Please supply an experiment\n")
        sys.exit()      

    logging.basicConfig(level=logging.INFO)

    expRoot     =   os.path.join("Data",args[0])
    expIni      =   os.path.join(expRoot,"experiment.ini")
    searchPath  =   os.path.join(expRoot,"Searches")

    if not os.path.exists(expIni):
        logging.error("No such experiment [%s]" % args[0])

    with CreateLiveBlob("cake.db",args[0]) as db:
        pass

