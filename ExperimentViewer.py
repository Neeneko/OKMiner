import optparse
import sys
import os

from Experiment import MinerExperiment
from Questions import MinerQuestions
from Profile import MatchProfile


class StatContainer(object):

    def __init__(self,qid):
        self.__qid      =   qid
        self.__weights  =   []

    def getId(self):
        return self.__qid

    def addWeight(self,weight):
        self.__weights.append(weight)

    def getCount(self):
        return len(self.__weights)

    def getScore(self):
        sum = 0.0
        for weight in self.__weights:
            sum += weight
        return sum

    def __cmp__(self,other):
        return cmp(self.getScore(),other.getScore())

if __name__ == "__main__":
    usage       =   "usage: %prog [options] folder"
    description =   "Views an experiment already run against OKCupid "
    parser = optparse.OptionParser(usage=usage,description=description)
    parser.add_option('-n', '--number', help="The top number of questions to output", type='int', default=128)

    options, args = parser.parse_args()

    if len(args) != 1:
        sys.stderr.write("Please supply folder name\n")
        sys.exit()      

    folderName = args[0]
    maxQuestions    =   16


    if not os.path.exists(folderName):
        sys.stderr.write("No such folder [%s]\n" % folderName)
        sys.exit()      
    questions   =   MinerQuestions()
    experiment  =   MinerExperiment()
    experiment.loadExperiment(folderName)
    sys.stderr.write("Loaded Experiment for [%s], [%s] Matches\n" % (experiment.getUserName(),experiment.getMatchCount()))
    sys.stderr.write("Total Questions [%s]\n" %  questions.getCount())

    aStats  =   {}
    for questionId in questions.getQuestionIds():
        aStats[questionId] = StatContainer(questionId)

    for (matchName,matchFile) in experiment.getMatches():
        matchProfile = MatchProfile()
        matchProfile.loadFromConfig(matchFile)
        sys.stderr.write("Loaded [%s] - [%d] Answers\n" % (matchProfile.Info["Name"],len(matchProfile.Answers)))
        for idx in range(len(matchProfile.Answers)):
            aStats[matchProfile.Answers[idx]].addWeight( float(idx)/float(len(matchProfile.Answers)))

    sortedStats = sorted(aStats.values())
    for idx in range(options.number):
        aStat = sortedStats[len(sortedStats) - idx - 1]
        sys.stderr.write("Question [%6d] Count [%4d] Weight [%4.2f] - %s\n" % (aStat.getId(),aStat.getCount(),aStat.getScore(),questions.getText(aStat.getId())))
