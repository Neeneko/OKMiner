import ConfigParser
import sys
import os

class MinerQuestions(object):

    def __init__(self):
        self.__dataPath     =   os.path.join(os.path.dirname(sys.modules[__name__].__file__), "Data")
        self.__dataName     =   os.path.join(self.__dataPath,"questions.ini")
        self.__config       =   ConfigParser.ConfigParser()
        self.__config.optionxform=str
        if not os.path.exists(self.__dataPath):
            sys.stderr.write("Data path does not exist, creating\n")
            os.mkdir(self.__dataPath)

        if os.path.exists(self.__dataName):
            self.__config.read(self.__dataName)

    def saveQuestions(self):
       with open(self.__dataName,'wb') as configFile:
            self.__config.write(configFile)

    def hasQuestion(self,question_id):
        return self.__config.has_section("%s" % question_id)

    def addQuestion(self,question_id,text,answers):
        self.__config.add_section("%s" % question_id)
        self.__config.set("%s" % question_id,"Text",text.encode('ascii','ignore'))
        for idx in range(len(answers)):
            self.__config.set("%s" % (question_id),"Answer_%d" % (idx+1),answers[idx].encode('ascii','ignore'))

    def getCount(self):
        return len(self.__config.sections())

    def getQuestionIds(self):
        return [int(x) for x in self.__config.sections()]

    def getText(self,question_id):
        return self.__config.get("%s" % question_id,"Text")

    def getAnswers(self,question_id):
        rv = []
        for i in range(8):
            qid = "%s" % (question_id)
            key = "Answer_%d" % (i+1)
            if self.__config.has_option(qid,key):
                rv.append( self.__config.get(qid,key))
        return rv
