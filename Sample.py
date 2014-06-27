import os
import optparse
import sys
import logging
import ConfigParser
import shutil
import glob
import json
import random
import time
from SessionManager import SessionManager


class MinerSample(object):

    class   MiniResult(object):
        def __init__(self,result):
            self.UserId     =   result["userid"]
            self.UserName   =   result["username"]
            self.Match      =   result["match_percentage"]

    PROPERTIES  =   {
                        "MaxSample"     :   "%s" % sys.maxint,
                        "MinMatch"      :   "0",
                        "Random"        :   "False"
                    }

    def __init__(self,experiment_name,sample_name):
        self.__rootPath             =   os.path.dirname(sys.modules[__name__].__file__)
        self.__dataPath             =   os.path.join(os.path.dirname(sys.modules[__name__].__file__), "Data")
        self.__expPath              =   os.path.join(self.__dataPath,experiment_name)
        self.__searchPath           =   os.path.join(self.__expPath,"Searches")
        self.__profilePath          =   os.path.join(self.__expPath,"Profiles")
        self.__answerPath           =   os.path.join(self.__expPath,"Answers")
        self.__configFile           =   os.path.join(self.__expPath,"experiment.ini")
        self.__expName              =   experiment_name
        self.__sampleName           =   sample_name
        self.__config               =   ConfigParser.ConfigParser()
        self.__config.optionxform   =   str

    def init(self):
        logging.info("Initializing Sample [%s] in Experiment [%s]" % (self.__sampleName,self.__expName))

        bigConfigPath   =   os.path.join(self.__rootPath,"Config","samples.ini")
        if not os.path.exists(bigConfigPath):
            raise RuntimError,"Global experiment list not found"

        bigConfig       =   ConfigParser.ConfigParser()
        bigConfig.optionxform=str
        bigConfig.read(bigConfigPath)
        if not bigConfig.has_section(self.__sampleName):
            raise RuntimeError,"No such sample [%s] in global list" % self.__sampleName     

        self.loadConfig()
        if self.__config.has_section("Sample"):
            logging.warn("Experiment has a sample already, clearing")
            self.__config.remove_section("Sample")
        if os.path.exists(self.__profilePath):
            logging.warn("Old profile directory exists, clearing")
            shutil.rmtree(self.__profilePath)
        os.mkdir(self.__profilePath)

        if os.path.exists(self.__answerPath):
            logging.warn("Old answer directory exists, clearing")
            shutil.rmtree(self.__answerPath)
        os.mkdir(self.__answerPath)
 

        self.__config.add_section("Sample")
        self.__config.set("Sample","Name",self.__sampleName)
        for k,v in MinerSample.PROPERTIES.iteritems():
            if bigConfig.has_option(self.__sampleName,k):
                self.__config.set("Sample",k,bigConfig.get(self.__sampleName,k))
            else:
                self.__config.set("Sample",k,v)

        self.saveConfig()

    def loadConfig(self):
        self.__config               =   ConfigParser.ConfigParser()
        self.__config.optionxform   =   str

        self.__config.read(self.__configFile)

    def saveConfig(self):
       with open(self.__configFile,'wb') as configFile:
            self.__config.write(configFile)

    def loadSearches(self):
        rv  =   {}
        for fileName in glob.glob(os.path.join(self.__searchPath,"*.json")):
            with open(fileName) as fp:
                data        =   json.load(fp)

            for result in data["amateur_results"]:
                rv[result["userid"]] = MinerSample.MiniResult(result)
        return rv

    def getUserName(self):
        return self.__config.get("Settings","UserName")


    def getMinMatch(self):
        return int(self.__config.get("Sample","MinMatch"))

    def isRandom(self):
        return self.__config.get("Sample","Random").upper() == "TRUE"

    def getMaxSample(self):
        return int(self.__config.get("Sample","MaxSample"))

    def filterSearches(self,users):
        rv  =   users

        if self.getMinMatch() > 0:
            logging.info("Filtering Matches below [%s]" % self.getMinMatch())
            temp  =   {}
            for k,v in users.iteritems():
                if v.Match > self.getMinMatch():
                    temp[k] = v
            rv = temp
        if self.isRandom():
            keys    =   rv.keys()
            random.shuffle(keys)
            temp = {}
            for key in keys:
                temp[key] = rv[key]
            rv = temp
 
        return rv

    def crawlProfiles(self,names):
        count   =   0
        idx     =   0
        session =   SessionManager.getSession()
        while True:

            if idx >= len(names):
                return

            if count >= self.getMaxSample():
                return

            name    =   names[idx]
            logging.info("[%s]" % name)
            count += 1
            #-----------------------------------------------------------------------------------------
            url = "http://www.okcupid.com/profile/%s?okc_api=1" % name
            try:
                logging.info(url)
                page = session.get(url)
            except requests.exceptions.ConnectionError:
                logging.warn("Connection error, sleeping 30 seconds")
                time.sleep(30)
                continue
            if page.status_code != 200:
                logging.warn("Page Error [%s:%s] sleeping 60 seconds" % (page.status_code,page.reason))
                time.sleep(30)
                continue

            data    =       json.loads(page.text)
            idx     +=  1
            if int(data["status"]) > 100:
                logging.warn("Profile returned status [%s:%s]" % (data["status"],data["status_str"]))
                continue
            userId      =   data["userid"]
            fileName    =   os.path.join(self.__profilePath,"%s.json" % userId)
            with open(fileName,'wb') as fp:
                json.dump(data,fp,indent=4, separators=(',', ': '))
            #-----------------------------------------------------------------------------------------
            url = "http://www.okcupid.com/profile/%s" % name
            try:
                logging.info(url)
                page = session.get(url)
            except requests.exceptions.ConnectionError:
                logging.warn("Connection error, sleeping 30 seconds")
                time.sleep(30)
                continue
            if page.status_code != 200:
                logging.warn("Page Error [%s:%s] sleeping 60 seconds" % (page.status_code,page.reason))
                time.sleep(30)
                continue

            fileName    =   os.path.join(self.__profilePath,"%s.html" % userId)
            with open(fileName,'wb') as fp:
                fp.write(page.text.encode("UTF-8"))
            #-----------------------------------------------------------------------------------------
            low =   1
            while True:
                url = "http://www.okcupid.com/profile/%s/questions?okc_api=1&low=%d" % (name,low)
                result = json.loads(session.get(url).text)
                try:
                    logging.info(url)
                    page = session.get(url)
                except requests.exceptions.ConnectionError:
                    logging.warn("Connection error, sleeping 30 seconds")
                    time.sleep(30)
                    continue
                if page.status_code != 200:
                    logging.warn("Page Error [%s:%s] sleeping 60 seconds" % (page.status_code,page.reason))
                    time.sleep(30)
                    continue

                data    =       json.loads(page.text)
                fileName   =  os.path.join(self.__answerPath,"%s.%s.json" % (userId,low))
                with open(fileName,'wb') as fp:
                    json.dump(data,fp,indent=4, separators=(',', ': '))

                if data["pagination"]["cur_last"] == data["pagination"]["last"]:
                    break
                else:
                    low += 10
                time.sleep(2)

            time.sleep(10)




def runSampler(sample):
    sample.init()
    searches    =   sample.loadSearches()
    logging.info("Total search size [%s]" % len(searches))
    filtered    =   sample.filterSearches(searches)
    logging.info("Filtered search size [%s]" % len(filtered))
    logging.info("Logging in as [%s]" % sample.getUserName())
    SessionManager.doLogin(sample.getUserName())
    
    #for k,v in filtered.iteritems():
    #    logging.info("[%32s] => [%2d][%s]" % (k,v.Match,v.UserName))
    sample.crawlProfiles([x.UserName for x in filtered.itervalues()])
    #sample.crawlProfiles(["Euroko","Euro_ko"])


if __name__ == "__main__":
    usage       =   "usage: %prog [options] experiment sample"
    description =   "Sample an experiment against OKCupid"
    parser = optparse.OptionParser(usage=usage,description=description)

    options, args = parser.parse_args()

    if len(args) != 2:
        sys.stderr.write("Please supply an experiment and sample\n")
        sys.exit()      

    logging.basicConfig(level=logging.INFO)
  
    experimentName  =   args[0]
    sampleName      =   args[1]
    sample          =   MinerSample(experimentName,sampleName)

    runSampler(sample)
