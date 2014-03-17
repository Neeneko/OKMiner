import os
import re
import sys
import glob
import base64
import optparse
import ConfigParser
from Profile import UserProfile
from ProfileManager import ProfileManager
from Questions import QuestionDB

class SetManager(object):

    def __init__(self):
        self.__setPath      =    os.path.join(os.path.dirname(sys.modules[__name__].__file__), "Sets")

        if not os.path.exists(self.__setPath):
            sys.stderr.write("Data path does not exist, creating\n")
            os.mkdir(self.__setPath)

    def saveSet(self,set_name,answers):
        config       =   ConfigParser.ConfigParser()

        config.optionxform=str
        fileName   =   os.path.join(self.__setPath,"%s.ini" % set_name)
        config.add_section("Answers")
        for k,v in answers.iteritems():
            if v.Explination is not None:
                config.set("Answers","%s" % k,"%s,%s,%s,%s" % (v.Selected,v.Accepted,v.Importance,base64.b64encode(v.Explination)))
            else:
                config.set("Answers","%s" % k,"%s,%s,%s" % (v.Selected,v.Accepted,v.Importance))
        with open(fileName,'wb') as fp:
            config.write(fp)

    def getSet(self,set_name):
        rv          =   {}
        config      =   ConfigParser.ConfigParser()
        config.optionxform=str
        config.read(os.path.join(self.__setPath,"%s.ini" % set_name))
        for k,v in config.items("Answers"):
            answer = UserProfile.UserAnswer( int(k) )
            values = re.split(",",v)
            answer.Selected         =   int(values[0])
            answer.Accepted         =   int(values[1])
            answer.Importance       =   int(values[2])
            if len(values) == 4:
                answer.Explination =   base64.b64decode(values[3])
            rv[ int(k) ] = answer
        return rv

    def getSetNames(self):
        fileNames = glob.glob(os.path.join(self.__setPath,"*.ini"))
        setNames = []
        for fileName in fileNames:
            root,_ = os.path.splitext(fileName)
            setNames.append(os.path.basename(root))
        return setNames

    @staticmethod
    def printSet(answer_set):
        sys.stderr.write("Set Contains %d of %d Questions\n" % (len(answer_set),len(QuestionDB.getQuestionIds())))
        for questionId,answer in answer_set.iteritems():
            text    =   QuestionDB.getText(questionId)
            sys.stderr.write("[%8d] Question:   %s\n" % (questionId,text))
            Answers = QuestionDB.getAnswers(questionId)
            for idx in range(len(Answers)):
                if idx+1 == answer.Selected:
                    selected = "[X]"
                else:
                    selected = "[ ]"

                if (1 << idx+1) & answer.Accepted:
                    accepted = "[X]"
                else:
                    accepted = "[ ]"

                sys.stderr.write("[%8d]\t%s%s %s\n" % (questionId,selected,accepted,Answers[idx]))
            sys.stderr.write("[%8d]\tImportance: %s\n" % (questionId,answer.Importance))
            sys.stderr.write("[%8d]\tExplination: %s\n" % (questionId,answer.Explination))
            sys.stderr.write("[%8d]\tRaw: (%s,%s,%s)\n" % (questionId,answer.Selected,answer.Accepted,answer.Importance))

    def doRestore(self,user_name,set_name):
        sys.stderr.write("Starting Restore\n")
        self.doClear(user_name)
        session     =   profileManager.doLogin(user_name)
        profile     =   UserProfile()
        restoreSet  =   self.getSet(set_name)
        for k,v in restoreSet.iteritems():
            liveAnswer  =   profile.getAnswerFromSession(session,k)
            sys.stderr.write("[%8d] - %s\n" % (k,liveAnswer.Selected))
            if liveAnswer.Selected != 0:
                sys.stderr.write("[%8d] - Already Set - we have a problem\n" % (k))
            else:
                sys.stderr.write("[%8d] - Starting Set\n" % (k))
                profile.setAnswerToSession(session,v)
        # we should validate here

    def doClear(self,user_name):
        sys.stderr.write("Starting Clear\n")
        session     =   profileManager.doLogin(user_name)
        profile =   UserProfile()
        profile.loadFromSession(session,userName)
        sys.stderr.write("Profile Has [%d] Answers\n" % len(profile.Answers))
        profile.clearAnswersFromSession(session)
        profile.loadFromSession(session,userName)
        sys.stderr.write("Profile Has [%d] Answers\n" % len(profile.Answers))

    def doDiff(self,user_name,set_name):
        session =   profileManager.doLogin(user_name)
        profile =   UserProfile()
        profile.loadFromSession(session,user_name)
        storedSet =  setManager.getSet(set_name)
        storedSetIds    =   set(storedSet.keys())
        profileSetIds   =   set(profile.Answers.keys())
        bothIds         =   profileSetIds.intersection(storedSetIds)
        diffIds         =   profileSetIds.symmetric_difference(storedSetIds)
        badIds          =   []
        for commonId in bothIds:
            if storedSet[commonId] != profile.Answers[commonId]:
                badIds.append(commonId)   
        sys.stderr.write("Stored [%d] Profile [%s]\n" % (len(storedSetIds),len(profileSetIds)))
        sys.stderr.write("Common [%d] Diff [%d] Bad [%d]\n" % (len(bothIds),len(diffIds),len(badIds)))
        for badId in badIds:
            sys.stderr.write("[%08d]\n" % badId)

        return len(badIds) != 0
 

if __name__ == "__main__":
    usage = "usage: %prog [options] username set/qid"
    parser = optparse.OptionParser()
    parser.add_option('-l','--list',help="List currently stored sets of questions",action="store_true",default=False)
    parser.add_option('-s','--save',help="Save set of questions from a user",action="store_true",default=False)
    parser.add_option('-r','--restore',help="Restore set of questions to a user",action="store_true",default=False)
    parser.add_option('-q','--query',help="Query answers contained within a set",action="store_true",default=False)
    parser.add_option('-e','--examine',help="Examine a profile's current answer(s)",action="store_true",default=False)
    parser.add_option('-c','--clear',help="Clear a profile's current answer(s)",action="store_true",default=False)
    parser.add_option('-d','--diff',help="compare profile to set",action="store_true",default=False)

    options, args = parser.parse_args()

    if not options.diff ^ options.query ^ options.list ^ options.save ^ options.restore ^ options.examine ^ options.clear:
        sys.stderr.write("Please select between list, save, restore, examine, clear, query, and diff\n")
        sys.exit()

    if (options.query or options.clear or options.query) and len(args) != 1:
        sys.stderr.write("Query and Clear take only one argument\n")
        sys.exit()

    if (options.examine) and len(args) != 1 and len(args) != 2:
        sys.stderr.write("Examine takes one or two arguments\n")
        sys.exit()

    if options.list and len(args) != 0:
        sys.stderr.write("List takes no arguments\n")
        sys.exit()

    if (options.save or options.restore or options.diff) and len(args) != 2:
        sys.stderr.write("Save, Restore and Diff take two arguments\n")
        sys.exit()

    setManager = SetManager()

    if (options.save or options.restore or options.examine or options.clear or options.diff):
        profileManager  =   ProfileManager()
        userName = args[0]
        if len(args) == 2:
            setName = args[1]
        if userName not in profileManager.getProfileNames():
            sys.stderr.write("No such profile stored\n")
            sys.exit(0)
        if options.examine:
            session =   profileManager.doLogin(userName)
            profile =   UserProfile()
            if len(args) == 2:
                answer = profile.getAnswerFromSession(session,int(args[1]))
                sys.stderr.write("Answer [%s]\n" % answer)
                setManager.printSet({answer.Id : answer})
            else:
                profile.loadFromSession(session,userName)
                setManager.printSet(profile.Answers)
        elif options.save:
            session =   profileManager.doLogin(userName)
            profile =   UserProfile()
            profile.loadFromSession(session,userName)
            setManager.saveSet(setName,profile.Answers)
        elif options.restore:
            setManager.doRestore(userName,setName)
        elif options.clear:
            setManager.doClear(userName)
        elif options.diff:
            setManager.doDiff(userName,setName)



    if options.query:
        setName = args[0]
        if setName not in setManager.getSetNames():
            sys.stderr.write("[%s] is not an available set\n" % setName)
            sys.exit(0)
        setManager.printSet(setManager.getSet(setName))


    if options.list:
        setNames = setManager.getSetNames()
        sys.stderr.write("[%d] total sets available\n" % (len(setNames)))
        for setName in setNames:
            sys.stderr.write("\t%s\n" % setName)

