import optparse
import sys
from ExperimentManager import ExperimentManager

if __name__ == "__main__":
    usage       =   "usage: %prog [options] experiment"
    description =   "Runs an experiment against OKCupid"
    parser = optparse.OptionParser(usage=usage,description=description)

    options, args = parser.parse_args()

    if len(args) != 1:
        sys.stderr.write("Please supply an experiment\n")
        sys.exit()      

    experimentName = args[0]
    experimentManager = ExperimentManager()

    if experimentName not in experimentManager.getExperimentNames():
        sys.stderr.write("Experiment [%s] not stored\n" % experimentName)
        sys.exit()

    experiment      =   experimentManager.createExperiment(experimentName)
    experiment.doExperiment()

