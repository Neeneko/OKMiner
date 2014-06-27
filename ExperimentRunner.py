import os
import optparse
import sys
import logging
import time
from Experiment import MinerExperiment
from SessionManager import SessionManager
from Search import *

def runSearches(experiment):
    logging.info("Age       [%s]" % str(experiment.getAgeRange()))
    logging.info("Location  [%s]" % str(experiment.getLocationRange()))
    logging.info("Gentation [%s]" % str(experiment.getGentationRange()))
    for age in experiment.getAgeRange():
        for location in experiment.getLocationRange():
            for gentation in experiment.getGentationRange():
                for rating in range(5):
                    rlow   =   rating*2000
                    rhigh   =   (rating+1)*2000-1
                    if int(location) == 0:
                        locationFilter  =   LocationAnywhereFilter()
                    else:
                        locationFilter  =   LocationIdFilter(location,50)

                    url = genSearchURL(MatchOrder("MATCH"),AgeFilter(age,age),LastOnFilter(LastOnFilter.WEEK),locationFilter,GentationFilter(gentation),PhotoFilter(False),StatusFilter(StatusFilter.ANY),RatingFilter(rlow,rhigh))
                    results         =   doSearchJSON(url)
                    for i in range(len(results)):
                        searchName  =   "%s.%s.%s.%s-%s.p%s.json" % (age,location,gentation,rlow,rhigh,i)
                        fileName    =   os.path.join(experiment.getSearchPath(),searchName)
                        with open(fileName,'wb') as fp:
                            json.dump(results[i],fp)
                    time.sleep(10)

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

    runSearches(experiment)


    """
    experimentName = args[0]
    experimentManager = ExperimentManager()

    if experimentName not in experimentManager.getExperimentNames():
        sys.stderr.write("Experiment [%s] not stored\n" % experimentName)
        sys.exit()

    experiment      =   experimentManager.createExperiment(experimentName)
    experiment.doExperiment()
    """

