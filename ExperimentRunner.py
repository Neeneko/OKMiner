import os
import optparse
import sys
import logging
import time
from Experiment import MinerExperiment
from SessionManager import SessionManager
from Search import *

def runSearches(experiment):
    allResults      =   set()
    duplicates      =   0
    empty           =   0
    searches        =   0
    logging.info("Age       [%s]" % str(experiment.getAgeRange()))
    logging.info("Location  [%s]" % str(experiment.getLocationRange()))
    logging.info("Gentation [%s]" % str(experiment.getGentationRange()))
    logging.info("Rating    [%s]" % str(experiment.getRatingSlices()))
    for age in experiment.getAgeRange():
        for (location,distance) in experiment.getLocationRange():
            if int(location) == 0 and int(distance) == 0:
                locationFilter  =   LocationAnywhereFilter()
            else:
                locationFilter  =   LocationIdFilter(location,distance)

            for gentation in experiment.getGentationRange():
                if experiment.getRatingSlices() == None:
                    time.sleep(10)
                    url = genSearchURL(MatchOrder("MATCH"),AgeFilter(age,age),LastOnFilter(LastOnFilter.WEEK),locationFilter,GentationFilter(gentation),PhotoFilter(False),StatusFilter(StatusFilter.ANY))
                    results         =   doSearchJSON(url)
                    searches        +=  1
                    if len(results) == 0:
                        empty       +=  1
                    for i in range(len(results)):
                        searchName      =   "%s.%s.%s.p%s.json" % (age,location,gentation,i)
                        fileName        =   os.path.join(experiment.getSearchPath(),searchName)
                        with open(fileName,'wb') as fp:
                            json.dump(results[i],fp,indent=4, separators=(',', ': '))
                        for result in results[i]["amateur_results"]:
                            uid = result["userid"]
                            if uid not in allResults:
                                allResults.add(uid)
                            else:
                                duplicates   +=  1

                else:
                    for rlow,rhigh in experiment.getRatingSlices():
                        url = genSearchURL(MatchOrder("MATCH"),AgeFilter(age,age),LastOnFilter(LastOnFilter.WEEK),locationFilter,GentationFilter(gentation),PhotoFilter(False),StatusFilter(StatusFilter.ANY),RatingFilter(rlow,rhigh))
                        results         =   doSearchJSON(url)
                        searches        +=  1
                        if len(results) == 0:
                            empty       +=  1
                        for i in range(len(results)):
                            searchName  =   "%s.%s.%s.%s-%s.p%s.json" % (age,location,gentation,rlow,rhigh,i)
                            fileName    =   os.path.join(experiment.getSearchPath(),searchName)
                            results[i]["filters"]["MinRating"]  =   rlow
                            results[i]["filters"]["MaxRating"]  =   rhigh
                            with open(fileName,'wb') as fp:
                                json.dump(results[i],fp,indent=4, separators=(',', ': '))
                            for result in results[i]["amateur_results"]:
                                uid = result["userid"]
                                if uid not in allResults:
                                    allResults.add(uid)
                                else:
                                    duplicates   +=  1
                        time.sleep(10)
    logging.info("**************************")
    logging.info("*Total Unique  [%8s]*" % len(allResults))
    logging.info("*Duplicates    [%8s]*" % duplicates)
    logging.info("*Searches      [%8s]*" % searches)
    logging.info("*Empty Results [%8s]*" % empty)
    logging.info("**************************")

if __name__ == "__main__":
    usage       =   "usage: %prog [options] experiment"
    description =   "Runs an experiment against OKCupid"
    parser = optparse.OptionParser(usage=usage,description=description)

    options, args = parser.parse_args()

    if len(args) != 1:
        sys.stderr.write("Please supply an experiment\n")
        sys.exit()      

    logging.basicConfig(level=logging.INFO)
  
    experimentName = args[0]
    experiment  =   MinerExperiment(experimentName)
    experiment.init()

    experiment.saveTimestamp("StartSearch")
    runSearches(experiment)
    experiment.saveTimestamp("EndSearch")


    """
    experimentName = args[0]
    experimentManager = ExperimentManager()

    if experimentName not in experimentManager.getExperimentNames():
        sys.stderr.write("Experiment [%s] not stored\n" % experimentName)
        sys.exit()

    experiment      =   experimentManager.createExperiment(experimentName)
    experiment.doExperiment()
    """

