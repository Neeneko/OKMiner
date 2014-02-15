import optparse
import sys
from Login import doLogin
from Session import MinerSession
from Experiment import MinerExperiment,doExperiment
from Questions import MinerQuestions

if __name__ == "__main__":
    usage       =   "usage: %prog [options] username"
    description =   "Runs an experiment against OKCupid using a profile"
    parser = optparse.OptionParser(usage=usage,description=description)

    options, args = parser.parse_args()

    if len(args) != 1:
        sys.stderr.write("Please supply username\n")
        sys.exit()      

    userName = args[0]


    session     =   MinerSession()
    experiment  =   MinerExperiment()
    questions   =   MinerQuestions()

    session.loadConfig()
    if userName not in session.getProfileNames():
        sys.stderr.write("Profile [%s] not already stored\n" % userName)
        sys.exit()

    if not doLogin(session,userName):
        sys.stderr.write("Profile login failure.\n")
        sys.exit()

    experiment.loadExperiment(userName)
    doExperiment(session,experiment,questions)
