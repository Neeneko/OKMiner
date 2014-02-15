import re
import ConfigParser
from lxml import html

class AbstractProfile(object):

    def __init__(self,session,user_name):
        page                        =   session.getSession().get('https://www.okcupid.com/profile/%s' % user_name)
        tree                        =   html.fromstring(page.text)
        self.Info                   =   {}
        self.Info["Name"]           =   tree.xpath('//span[@id="basic_info_sn"]/text()')[0]
        self.Info["Age"]            =   int(tree.xpath('//span[@id="ajax_age"]/text()')[0])
        self.Info["Gender"]         =   tree.xpath('//span[@id="ajax_gender"]/text()')[0]
        self.Info["Orientation"]    =   tree.xpath('//span[@id="ajax_orientation"]/text()')[0]
        self.Info["Status"]         =   tree.xpath('//span[@id="ajax_status"]/text()')[0]
        self.Info["Location"]       =   tree.xpath('//span[@id="ajax_location"]/text()')[0]

        self.Details                =   {}
        labelList   =   tree.xpath('//div/dl/dt/text()')
        infoList    =   tree.xpath('//div/dl/dd/text()')
        for idx in range(len(labelList)):
            self.Details[labelList[idx]] = infoList[idx].encode('ascii','ignore').strip() 

        self.LookingFor             =   {}
        self.LookingFor["Gentation"]=   tree.xpath('//li[@id="ajax_gentation"]/text()')[0]
        self.LookingFor["Near"]     =   tree.xpath('//li[@id="ajax_near"]/text()')[0]
        self.LookingFor["Single"]   =   tree.xpath('//li[@id="ajax_single"]/text()')[0]
        self.LookingFor["Seeking"]  =   tree.xpath('//li[@id="ajax_lookingfor"]/text()')[0].strip()

        ageRaw                      =   re.split(' ',tree.xpath('//li[@id="ajax_ages"]/text()')[0])
        ageList                     =   re.split(u'\u2013',ageRaw[1])
        self.LookingFor["AgeLow"]   =   int(ageList[0])
        self.LookingFor["AgeHigh"]  =   int(ageList[1])

        self.Essays                 =   []
        for idx in range(10):
            self.Essays.append(tree.xpath('//div[@id="essay_text_%d"]/text()' % idx)[0])

    def saveProfile(self,file_name):

        parser       =   ConfigParser.ConfigParser()
        parser.optionxform=str

        self.fillConfig(parser)

        with open(file_name,'wb') as fp:
            parser.write(fp)

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

class UserProfile(AbstractProfile):

    class UserQuestion(object):
        def __init__(self,qid):
            self.Id         =   qid
            self.Text       =   None
            self.Answers    =   []
            #self.Selected   =   None
            #self.Accepted   =   []
            #self.Importance =   None

    class UserAnswer(object):
        def __init__(self,qid):
            self.Id         =   qid
            self.Selected   =   None
            self.Accepted   =   None
            self.Importance =   None

    def __init__(self,session,user_name):
        AbstractProfile.__init__(self,session,user_name)
        
        self.Answers    =   {}
        self.Questions  =   []
        link = 'http://www.okcupid.com/profile/%s/questions' % user_name
        while True:
            nextLink = self.__fillFromLink(link,session)
            if nextLink is None:
                break;
            link = 'http://www.okcupid.com%s' % nextLink

    def __fillFromLink(self,link,session):
        print "Filling From [%s]" % link
        page = session.getSession().get(link)
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
            question    =   UserProfile.UserQuestion(questionId)
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
    pass

