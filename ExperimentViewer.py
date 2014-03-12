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
    minAnswers      =   16
    profileAge      =   35


    if not os.path.exists(folderName):
        sys.stderr.write("No such folder [%s]\n" % folderName)
        sys.exit()      
    questions   =   MinerQuestions()
    experiment  =   MinerExperiment()
    experiment.loadExperiment(folderName)
    sys.stderr.write("Loaded Experiment for [%s], [%s] Matches\n" % (experiment.getUserName(),experiment.getMatchCount()))
    sys.stderr.write("Total Questions [%s]\n" %  questions.getCount())

    matches =   []
    for (matchName,matchFile) in experiment.getMatches():
        if os.path.exists(matchFile):
            matchProfile = MatchProfile()
            matchProfile.loadFromConfig(matchFile)
            sys.stderr.write("Loaded Match [%s] - [%d] Answers\n" % (matchProfile.Info["Name"],len(matchProfile.Answers)))
            if len(matchProfile.Answers) < minAnswers:
                continue
            if profileAge < int(matchProfile.LookingFor["AgeLow"]):
                continue
            if profileAge > int(matchProfile.LookingFor["AgeHigh"]):
                continue
            matches.append(matchProfile)

    if experiment.getIncludeEnemy():
        enemies = []
        for (matchName,matchFile) in experiment.getEnemies():
            if os.path.exists(matchFile):
                matchProfile = MatchProfile()
                matchProfile.loadFromConfig(matchFile)
                sys.stderr.write("Loaded Enemy [%s] - [%d] Answers\n" % (matchProfile.Info["Name"],len(matchProfile.Answers)))
                if len(matchProfile.Answers) < minAnswers:
                    continue
                if profileAge < int(matchProfile.LookingFor["AgeLow"]):
                    continue
                if profileAge > int(matchProfile.LookingFor["AgeHigh"]):
                    continue

                enemies.append(matchProfile)

    report    =   sys.stdout

    def WriteHeader(note):
        report.write("%s\n" % ("="*64))
        report.write("%s    %-48s    %s\n" % ( ("="*4),note,("="*4)))
        report.write("%s\n" % ("="*64))

    WriteHeader("Basics")
    report.write("Minimum Answers    [%s]\n" % minAnswers)
    report.write("Maxiumum Questions [%s]\n" % maxQuestions)
    if len(experiment.getMatches()) == len(matches):
        report.write("Total Matches      [%s]\n" % len(matches))
    else:
        report.write("Total Matches      [%s] Filtered [%s]\n" % (len(matches),len(experiment.getMatches()) - len(matches)))

    if experiment.getIncludeEnemy():
        if len(experiment.getEnemies()) == len(enemies):
            report.write("Total Enemies      [%s]\n" % len(enemies))
        else:
            report.write("Total Enemies      [%s] Filtered [%s]\n" % (len(enemies),len(experiment.getEnemies()) - len(enemies)))


    def WriteStat(name,group,field,profiles):
        rv = {}
        maxValueSize    =   len(field)
        for profile in profiles:
            groupDict   = getattr(profile,group)
            value       = groupDict[field]
            commaIndex  = value.find(",")
            if commaIndex != -1:
                value = value[:commaIndex]
            elif len(value) == 0:
                value = "No Answer"

            if len(value)>maxValueSize:
                maxValueSize = len(value)

            if value not in rv:
                rv[value] = {}
                rv[value]["Total"] = 0
            
            match       =   min(99,profile.Percentages[name])
            
            bin = match - match%10
            if bin not in rv[value]:
                rv[value][bin] = 0
            rv[value][bin] += 1
            rv[value]["Total"] += 1

        headerFmt = "[%%%ss]" % maxValueSize
        header  =   headerFmt % field
        for i in range(10):
            header += "[%2d%%]" % ((9-i)*10)
        header += "[Total]\n"
        report.write(header)

        for key in sorted(rv.keys()):
            line = headerFmt % key
            for i in range(10):
                bin = ((9-i)*10)
                if bin in rv[key]:
                    line += "[%3d]" % rv[key][bin]
                else:
                    line += "     "
            if rv[key]["Total"] == 0:
                line += "       \n"
            else:
                line += "[ %2d%% ]\n" % (100*(rv[key]["Total"])/len(profiles))

            report.write(line)

    def ProcessProfiles(name,profiles):
        aStats  =   {}
        for questionId in questions.getQuestionIds():
            aStats[questionId] = StatContainer(questionId)

        for profile in profiles:
            for idx in range(len(profile.Answers)):
                aStats[profile.Answers[idx]].addWeight( float(idx)/float(len(profile.Answers)))
        WriteHeader("%s - Answers" % name)
        sortedStats = sorted(aStats.values())
        for idx in range(options.number):
            aStat = sortedStats[len(sortedStats) - idx - 1]
            report.write("Question [%6d] Count [%4d] Weight [%4.2f] - %s\n" % (aStat.getId(),aStat.getCount(),aStat.getScore(),questions.getText(aStat.getId())))

        
        WriteStat(name,"Info","Age",profiles)
        WriteStat(name,"Info","Orientation",profiles)
        WriteStat(name,"Info","Location",profiles)
        WriteStat(name,"Details","Relationship Type",profiles)
        WriteStat(name,"Details","Smokes",profiles)
        WriteStat(name,"Details","Religion",profiles)
        WriteStat(name,"Details","Ethnicity",profiles)
        WriteStat(name,"LookingFor","Gentation",profiles)

    ProcessProfiles("Match",matches)
    if experiment.getIncludeEnemy():
        ProcessProfiles("Enemy",enemies)
    WriteHeader("Done")
