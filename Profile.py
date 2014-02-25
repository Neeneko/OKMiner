import re
import sys
import ConfigParser
import optparse
#from Login import doConnectWithoutLogin
from Session import MinerSession
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
            self.Selected   =   None
            self.Accepted   =   None
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
        print "Filling From [%s]" % link
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
            #----------------------------------------------------------------------------
            question    =   AbstractProfile.Question(questionId)
            question.Text = tree.xpath('//p[@id="qtext_%d"]/text()' % questionId)[0].encode('ascii','ignore').strip() 
            labels = tree.xpath('//form[@id="answer_%s"]/label/text()' % questionId)
            count   =    len(tree.xpath('//form[@id="answer_%s"]/label/input[@name="my_answer"]' % questionId))
            question.Answers  = labels[:count]
            self.Questions.append(question)
            #----------------------------------------------------------------------------
            answer      =   UserProfile.UserAnswer(questionId)
            answer.Selected = int(tree.xpath('//div/input[@id="question_%s_answer"]/@value' % questionId)[0])
            answer.Accepted = int(tree.xpath('//div/input[@id="question_%s_match_answers"]/@value' % questionId)[0])

            answer.Importance = int(tree.xpath('//div/input[@id="question_%s_importance"]/@value' % questionId)[0])
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

    def __fillFromLink(self,link,session):
        print "Filling From [%s]" % link
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
            #----------------------------------------------------------------------------
            question    =   AbstractProfile.Question(questionId)
            question.Text = tree.xpath('//p[@id="qtext_%d"]/text()' % questionId)[0].encode('ascii','ignore').strip() 
            labels = tree.xpath('//form[@id="answer_%s"]/label/text()' % questionId)
            count   =    len(tree.xpath('//form[@id="answer_%s"]/label/input[@name="my_answer"]' % questionId))
            question.Answers  = [ x.encode('ascii','ignore').strip() for x in labels[:count] ] 
            self.Questions.append(question)
            self.Answers.append(questionId)

        nextLink = tree.xpath('//li[@class="next"]/a/@href')
        if len(nextLink) != 0:
            return nextLink[0]
        else:
            return None

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

if __name__ == "__main__":
    usage = "usage: %prog [options] matchname"
    parser = optparse.OptionParser()
    options, args = parser.parse_args()

    if len(args) != 1:
        sys.stderr.write("Please supply profile examine\n")
    matchName = args[0]


    session         =   MinerSession()
    doConnectWithoutLogin(session)
    matchProfile    =   MatchProfile(session,matchName)
    rv = matchProfile.saveToString()
    sys.stderr.write(rv)

