import ConfigParser
import sys
import os

class QuestionConfig(object):

    def __init__(self):
        self.dataPath     =   os.path.join(os.path.dirname(sys.modules[__name__].__file__), "Data")
        self.dataName     =   os.path.join(self.dataPath,"questions.ini")
        self.config       =   ConfigParser.ConfigParser()
        self.config.optionxform=str
        if not os.path.exists(self.dataPath):
            sys.stderr.write("Data path does not exist, creating\n")
            os.mkdir(self.dataPath)

        sys.stderr.write("Loading Questions [%s]\n" % self.dataName)
        if os.path.exists(self.dataName):
            self.config.read(self.dataName)

    def saveQuestions(self):
       with open(self.dataName,'wb') as configFile:
            self.config.write(configFile)



GLOBAL_QUESTION_CONFIG  =   None

def getConfig():
    global GLOBAL_QUESTION_CONFIG
    if GLOBAL_QUESTION_CONFIG is None:
        GLOBAL_QUESTION_CONFIG = QuestionConfig()
    return GLOBAL_QUESTION_CONFIG

class QuestionDB(object):

    @staticmethod
    def hasQuestion(question_id):
        return getConfig().config.has_section("%s" % question_id)

    @staticmethod
    def addQuestion(question_id,text,answers):
        getConfig().config.add_section("%s" % question_id)
        getConfig().config.set("%s" % question_id,"Text",text.encode('ascii','ignore'))
        for idx in range(len(answers)):
            getConfig().config.set("%s" % (question_id),"Answer_%d" % (idx+1),answers[idx].encode('ascii','ignore'))
        getConfig().saveQuestions()

    @staticmethod
    def getCount():
        return len(getConfig().config.sections())

    @staticmethod
    def getQuestionIds():
        return [int(x) for x in getConfig().config.sections()]

    @staticmethod
    def getText(question_id):
        return getConfig().config.get("%s" % question_id,"Text")

    @staticmethod
    def getAnswers(question_id):
        rv = []
        for i in range(8):
            qid = "%s" % (question_id)
            key = "Answer_%d" % (i+1)
            if getConfig().config.has_option(qid,key):
                rv.append( getConfig().config.get(qid,key))
        return rv


