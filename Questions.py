import ConfigParser
import sys
import os

class MinerQuestions(object):

    def __init__(self):
        self.__dataPath     =   os.path.join(os.path.dirname(sys.modules[__name__].__file__), "Data")
        self.__dataName     =   os.path.join(self.__dataPath,"questions.ini")
        self.__config       =   ConfigParser.ConfigParser()
        self.__config.optionxform=str

    def loadQuestions(self):
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
        self.__config.set("%s" % question_id,"Text",text)
        for idx in range(len(answers)):
            self.__config.set("%s" % (question_id),"Answer_%d" % (idx+1),answers[idx])

    def getCount(self):
        return len(self.__config.sections())

    def getQuestionIds(self):
        return [int(x) for x in self.__config.sections()]

    def getText(self,question_id):
        return self.__config.get("%s" % question_id,"Text")
