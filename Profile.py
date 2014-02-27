import re
import sys
import ConfigParser
import optparse
#from Login import doConnectWithoutLogin
#from Session import MinerSession
from ProfileManager import ProfileManager
from StringIO import StringIO
from lxml import html

class AbstractProfile(object):

    class Question(object):
        def __init__(self,qid):
            self.Id         =   qid
            self.Text       =   None
            self.Answers    =   []

    def __init__(self):
        self.Info                   =   {}
        self.Details                =   {}
        self.LookingFor             =   {}
        self.Essays                 =   []



    def loadFromSession(self,session,user_name):
        page                        =   session.get('https://www.okcupid.com/profile/%s' % user_name)
        tree                        =   html.fromstring(page.text)
        self.Info["Name"]           =   tree.xpath('//span[@id="basic_info_sn"]/text()')[0]
        self.Info["Age"]            =   int(tree.xpath('//span[@id="ajax_age"]/text()')[0])
        self.Info["Gender"]         =   tree.xpath('//span[@id="ajax_gender"]/text()')[0]
        self.Info["Orientation"]    =   tree.xpath('//span[@id="ajax_orientation"]/text()')[0]
        self.Info["Status"]         =   tree.xpath('//span[@id="ajax_status"]/text()')[0]
        self.Info["Location"]       =   tree.xpath('//span[@id="ajax_location"]/text()')[0]

        labelList   =   tree.xpath('//div/dl/dt/text()')
        infoList    =   tree.xpath('//div/dl/dd/text()')
        for idx in range(len(labelList)):
            self.Details[labelList[idx]] = infoList[idx].encode('ascii','ignore').strip() 

        self.LookingFor["Gentation"]=   tree.xpath('//li[@id="ajax_gentation"]/text()')[0]
        self.LookingFor["Near"]     =   tree.xpath('//li[@id="ajax_near"]/text()')[0]
        self.LookingFor["Single"]   =   tree.xpath('//li[@id="ajax_single"]/text()')[0]
        self.LookingFor["Seeking"]  =   tree.xpath('//li[@id="ajax_lookingfor"]/text()')[0].strip()

        ageRaw                      =   re.split(' ',tree.xpath('//li[@id="ajax_ages"]/text()')[0])
        ageList                     =   re.split(u'\u2013',ageRaw[1])
        self.LookingFor["AgeLow"]   =   int(ageList[0])
        self.LookingFor["AgeHigh"]  =   int(ageList[1])

        for idx in range(10):
            try:
                self.Essays.append(tree.xpath('//div[@id="essay_text_%d"]/text()' % idx)[0].encode('ascii','ignore').strip() )
            except IndexError:
                self.Essays.append(None)

    def loadFromConfig(self,file_name):
        parser       =   ConfigParser.ConfigParser()
        parser.optionxform=str
        parser.read(file_name)


        self.drainConfig(parser)

    def saveProfile(self,file_name):

        parser       =   ConfigParser.ConfigParser()
        parser.optionxform=str

        self.fillConfig(parser)

        with open(file_name,'wb') as fp:
            parser.write(fp)

    def saveToString(self):
        parser       =   ConfigParser.ConfigParser()
        parser.optionxform=str

        self.fillConfig(parser)

        fakeFp  =   StringIO()
        parser.write(fakeFp)
        rv = fakeFp.getvalue()
        fakeFp.close()
        return rv

    def fillConfig(self,config):
        config.add_section("Info")
        for k,v in self.Info.iteritems():
            config.set("Info",k,v)

        config.add_section("Details")
        for k,v in self.Details.iteritems():
            config.set("Details",k,v)

        config.add_section("LookingFor")
        for k,v in self.LookingFor.iteritems():
            config.set("LookingFor",k,v)

        config.add_section("Essays")
        for idx in range(len(self.Essays)):
            config.set("Essays","Essay_%02d" % idx,self.Essays[idx])

    def drainConfig(self,config):
        for (key,value) in config.items("Info"):
            self.Info[key] = value

        for (key,value) in config.items("Details"):
            self.Details[key] = value

        for (key,value) in config.items("LookingFor"):
            self.LookingFor[key] = value
        
        for idx in range(10):
            if (config.get("Essays","Essay_%02d" % idx)) != "None":
                self.Essays.append(config.get("Essays","Essay_%02d" % idx))
            else:
                self.Essays.append(None)

class UserProfile(AbstractProfile):

    class UserAnswer(object):
        def __init__(self,qid):
            self.Id         =   qid
            self.Selected   =   0
            self.Accepted   =   0
            self.Importance =   None

    def __init__(self):
        AbstractProfile.__init__(self)
        self.Answers    =   {}
        self.Questions  =   []

    def loadFromSession(self,session,user_name):
        AbstractProfile.loadFromSession(self,session,user_name)
        link = 'http://www.okcupid.com/profile/%s/questions' % user_name
        while True:
            nextLink = self.__fillFromLink(link,session)
            if nextLink is None:
                break;
            link = 'http://www.okcupid.com%s' % nextLink

    def __fillFromLink(self,link,session):
        sys.stderr.write("Filling From [%s]\n" % link)
        page = session.get(link)
        tree            =   html.fromstring(page.text)
        questionIds     =   []
        for divId in tree.xpath('//div[@id]/@id'):
            if divId.startswith("question"):
                splitList = re.split("_",divId)
                if len(splitList) != 2:
                    continue
                try:
                    questionId = int(splitList[1])
                    questionIds.append(questionId)
                except ValueError:
                    pass 
        for questionId in questionIds:
            #sys.stderr.write("QuestionId [%d]\n" % questionId)
            #----------------------------------------------------------------------------
            question            =   AbstractProfile.Question(questionId)
            question.Text       =   tree.xpath('//div[@id="qtext_%d"]/p/text()' % questionId)[0].encode('ascii','ignore').strip() 
            answers             =   tree.xpath('//ul[@id="self_answers_%s"]/li/text()' % questionId)
            question.Answers    =   answers
            self.Questions.append(question)
            #----------------------------------------------------------------------------
            answer      =   UserProfile.UserAnswer(questionId)
            selected = tree.xpath('//form[@name="answer_%s"]/div/input[@name="my_answer"]' % questionId)

            for idx in range(len(selected)):
                if "checked" in selected[idx].values():
                    answer.Selected = idx+1

            acceptable  = tree.xpath('//form[@name="answer_%s"]/div[@class="container acceptable_answers"]/input[@checked]/@value' % questionId)
            for accept in acceptable:
                if accept == 'irrelevant':
                    continue
                answer.Accepted += (1<<(int(accept)))
            importance = tree.xpath('//form[@name="answer_%s"]/div[@class="container importance"]/div[@class="importance_radios"]/input[@checked]/@value' % questionId)
            if len(importance) == 1:
                answer.Importance = int(importance[0])
            if answer.Selected != 0:
                self.Answers[questionId] = answer
        nextLink = tree.xpath('//li[@class="next"]/a/@href')
        if len(nextLink) != 0:
            return nextLink[0]
        else:
            return None

    def fillConfig(self,config):
        AbstractProfile.fillConfig(self,config)
        config.add_section("Answers")
        for k,v in self.Answers.iteritems():
            config.set("Answers","%s" % k,"%s,%s,%s" % (v.Selected,v.Accepted,v.Importance))

    def printAnswers(self):
        sys.stderr.write("[%d] Total Questiosn\n" % len(self.Questions))
        for question in self.Questions:
            if question.Id not in self.Answers:
                continue
            sys.stderr.write("[%8d] Question:   %s\n" % (question.Id,question.Text))
            for idx in range(len(question.Answers)):
                if idx+1 == self.Answers[question.Id].Selected:
                    selected = "[X]"
                else:
                    selected = "[ ]"

                if (1 << idx+1) & self.Answers[question.Id].Accepted:
                    accepted = "[X]"
                else:
                    accepted = "[ ]"

                sys.stderr.write("[%8d]\t%s%s %s\n" % (question.Id,selected,accepted,question.Answers[idx]))
            sys.stderr.write("[%8d]\tImportance: %s\n" % (question.Id,self.Answers[question.Id].Importance))


class MatchProfile(AbstractProfile):

    def __init__(self):
        AbstractProfile.__init__(self)
        self.Questions  =   []
        self.Answers    =   []

    def loadFromSession(self,session,user_name):
        AbstractProfile.loadFromSession(self,session,user_name)
        link = 'http://www.okcupid.com/profile/%s/questions?she_care=1' % user_name
        while True:
            nextLink = self.__fillFromLink(link,session)
            if nextLink is None:
                break;
            link = 'http://www.okcupid.com%s' % nextLink

    def fillConfig(self,config):
        AbstractProfile.fillConfig(self,config)
        config.add_section("Answers")
        for idx in range(len(self.Answers)):
            config.set("Answers","%d" % idx,self.Answers[idx])

    def drainConfig(self,config):
        AbstractProfile.drainConfig(self,config)
        keys = sorted(config.options("Answers"))
        for key in keys:
            self.Answers.append(int(config.get("Answers",key)))

    def __fillFromLink(self,link,session):
        sys.stderr.write("Filling From [%s]\n" % link)
        page = session.get(link)
        tree            =   html.fromstring(page.text)
        questionIds     =   []
        for divId in tree.xpath('//div[@id]/@id'):
            if divId.startswith("question"):
                splitList = re.split("_",divId)
                if len(splitList) != 2:
                    continue
                try:
                    questionId = int(splitList[1])
                    questionIds.append(questionId)
                except ValueError:
                    pass 
        for questionId in questionIds:
            #sys.stderr.write("QuestionId [%d]\n" % questionId)
            #----------------------------------------------------------------------------
            question            =   AbstractProfile.Question(questionId)
            question.Text       =   tree.xpath('//div[@id="qtext_%d"]/p/text()' % questionId)[0].encode('ascii','ignore').strip() 

            answers = tree.xpath('//form[@name="answer_%s"]/div/label[@class="radio"]/text()' % questionId)
            question.Answers    =   answers
            self.Questions.append(question)
            #----------------------------------------------------------------------------
            self.Answers.append(questionId)
            #----------------------------------------------------------------------------
        nextLink = tree.xpath('//li[@class="next"]/a/@href')
        if len(nextLink) != 0:
            return nextLink[0]
        else:
            return None

    def printAnswers(self):
        sys.stderr.write("[%d] Total Questiosn\n" % len(self.Questions))
        for question in self.Questions:
            if question.Id not in self.Answers:
                continue
            sys.stderr.write("[%8d] Question:   %s\n" % (question.Id,question.Text))
            for idx in range(len(question.Answers)):
                sys.stderr.write("[%8d]\t%s\n" % (question.Id,question.Answers[idx]))



if __name__ == "__main__":
    usage = "usage: %prog [options] username matchname"
    parser = optparse.OptionParser()
    options, args = parser.parse_args()

    if len(args) == 1:
        userName    =   args[0]
        matchName   =   args[0]
    elif len(args) == 2:
        userName    =   args[0]
        matchName   =   args[1]
    else:
        parser.print_help()
        sys.exit()


    profileManager  =   ProfileManager()
    session         =   profileManager.doLogin(userName)
    if userName == matchName:
        profile     =   UserProfile()
    else:
        profile     =   MatchProfile()

    profile.loadFromSession(session,matchName)
    sys.stderr.write(profile.saveToString())
    profile.printAnswers()

