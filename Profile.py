import re
import sys
import ConfigParser
import optparse
import time
import urllib
from StringIO import StringIO
from lxml import html

from ProfileManager import ProfileManager
from Questions import QuestionDB
#-------------------------------------------------------------------------------
"""
import logging
import httplib
httplib.HTTPConnection.debuglevel = 1

logging.basicConfig() 
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True
"""
#-------------------------------------------------------------------------------



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
        self.Info["Age"]            =   tree.xpath('//span[@id="ajax_age"]/text()')[0]
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
        self.LookingFor["AgeLow"]   =   ageList[0]
        self.LookingFor["AgeHigh"]  =   ageList[1]

        for k in self.LookingFor.keys():
            self.LookingFor[k] = self.LookingFor[k].encode('ascii','ignore').strip() 

        for k in self.Info.keys():
            self.Info[k] = self.Info[k].encode('ascii','ignore').strip() 

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

    def getUserName(self):
        return self.Info["Name"]

class UserProfile(AbstractProfile):

    class UserAnswer(object):
        def __init__(self,qid):
            self.Id             =   qid
            self.Selected       =   0
            self.Accepted       =   0
            self.Importance     =   None
            self.Explination    =   None

        def __eq__(self,other):
            return self.Id == other.Id \
                and self.Selected == other.Selected \
                and self.Accepted == other.Accepted \
                and self.Importance == other.Importance \
                and self.Explination == other.Explination

        def __ne__(self,other):
            return not self.__eq__(other)

    def __init__(self):
        AbstractProfile.__init__(self)
        self.Answers    =   {}
        self.TargetId   =   None

    def loadFromSession(self,session,user_name):
        AbstractProfile.loadFromSession(self,session,user_name)
        self.Answers    =   {}
        link = 'http://www.okcupid.com/profile/%s/questions' % user_name
        while True:
            nextLink = self.__fillFromLink(link,session)
            if nextLink is None:
                break;
            link = 'http://www.okcupid.com%s' % nextLink

    def clearAnswersFromSession(self,session):
        sys.stderr.write("Clearing Answers for [%s]\n" % self.getUserName())
        session.post("http://www.okcupid.com/questions",data={"clear_all" : "1"})
        link = "http://www.okcupid.com/poststat=bigdig - action - clear all&value=1&type=counter"
        session.get(link)
        sys.stderr.write("Done Clearing [%s]\n" % self.getUserName())

    def getAnswerFromSession(self,session,question_id):
        link        =   "http://www.okcupid.com/questions?rqid=%d" % question_id
        page        =   session.get(link)
        tree        =   html.fromstring(page.text)
        answer      =   UserProfile.UserAnswer(question_id)
        selected    =   tree.xpath('//div[@id="new_question"]/div/div/div/form[@name="answer_%s"]/div/input[@name="my_answer"]' % (question_id))

        for idx in range(len(selected)):
            if "checked" in selected[idx].values():
                answer.Selected = idx+1

        acceptable  = tree.xpath('//div[@id="new_question"]/div/div/div/form[@name="answer_%s"]/div[@class="container acceptable_answers"]/input[@checked]/@value' % question_id)
        filtered    =   []
        for idx in range(len(acceptable)):
            if "disabled" not in selected[idx].values():
                filtered.append(selected[idx])

        for accept in acceptable:
            if accept == 'irrelevant':
                continue
            answer.Accepted += (1<<(int(accept)))
        importance = tree.xpath('//div[@id="new_question"]/div/div/div/form[@name="answer_%s"]/div[@class="container importance"]/div[@class="importance_radios"]/input[@checked]/@value' % question_id)
        if len(importance) == 1:
            answer.Importance = int(importance[0])

        explinations = tree.xpath('//textarea[@id="answer_%s_explanation"]' % question_id)
        #sys.stderr.write("explinations [%s]\n" % explinations)
        #sys.stderr.write("All textarea\n")
        #for area in tree.xpath('//textarea'):
        #    sys.stderr.write("[%s] - %s\n" % (area.values(),area.text))
        
        for explination in explinations:
            if "disabled" not in explination.values():
                answer.Explination = explination.text


        #if len(explination) == 1:
        #    answer.Explination = explination[0]
        return answer 

    def setAnswerToSession(self,session,answer):
        sys.stderr.write("[%08s] - Uploading Answer [%s,%s,%s,%s]\n" % (answer.Id,answer.Selected,answer.Accepted,answer.Importance,answer.Explination))

        if self.TargetId is None:
            sys.stderr.write("[%08s] - TargetId Not Set, Getting\n" % (answer.Id))

            link        =   "http://www.okcupid.com/questions?rqid=%d" % answer.Id
            page        =   session.get(link)
            tree        =   html.fromstring(page.text)
 
            targetIds   = tree.xpath('//div[@id="questions_meta"]/input[@id="target_userid"]/@value')
            assert len(targetIds) == 1
            self.TargetId   =   targetIds[0]

        sys.stderr.write("[%08s] - TargetId [%s]\n" % (answer.Id,self.TargetId))

        payload     =   {
                            "ajax":             "1",
                            "submit":           "1",
                            "answer_question":  "1",
                            "skip":             "0",
                            "show_all":         "0",
                            "targetid":         "%s" % self.TargetId,
                            "qid":              "%s" % answer.Id,
                            "is_new":           "1",
                            "answers":          "%s" % answer.Selected,
                            #"matchanswers":     "%s" % answer.Accepted,
                            "importance":       "%s" % answer.Importance,
                            "is_public":        "1",      
                            #"note":             "",
                            "delete_note":      "0",
                        }
        payloadStr  =   urllib.urlencode(payload)
        payloadStr  +=  "&"
        if answer.Explination is None:
            payloadStr += urllib.urlencode({"note":""})
        else:
            payloadStr += urllib.urlencode({"note":answer.Explination})

        #TODO - this is very naughty and bad, FIX THIS
        if int(answer.Importance) == 5:
            payloadStr += "&matchanswers=irrelevant"
        else:
            accepted    =   []
            for idx in range(8):
                if (1 << idx+1) & answer.Accepted:
                    accepted.append( idx+1 )

            for accept in accepted:
                payloadStr += "&matchanswers=%d" % accept

        link        =   "http://www.okcupid.com/questions/ask"
        headers     =   {
                            "Accept" : "application/json, text/javascript, */*; q=0.01",
                            "Accept-Encoding" : "gzip, deflate",
                            "Content-Type" : "application/x-www-form-urlencoded; charset=UTF-8",
                            "X-Requested-With" : "XMLHttpRequest",
                            "Referer" :  "http://www.okcupid.com/questions?rqid=%d" % answer.Id,

                            "Connection" : "keep-alive"
                        }

        response    =   session.post(link,data=payloadStr)
        #sys.stderr.write("[%08s] - Response [%s]\n" % (answer.Id,response.status_code))
        #sys.stderr.write("[%08s] - URL      [%s]\n" % (answer.Id,response.url))
        #sys.stderr.write("[%08s] - Headers  [%s]\n" % (answer.Id,response.headers))
        #sys.stderr.write("[%08s] - Cookies  [%s]\n" % (answer.Id,response.cookies))
        #sys.stdout.write("\n%s\n" % response.text)
        time.sleep(1)
        newAnswer   =   self.getAnswerFromSession(session,answer.Id)
        sys.stderr.write("[%08s] - New      [%s,%s,%s,%s]\n" % (newAnswer.Id,newAnswer.Selected,newAnswer.Accepted,newAnswer.Importance,newAnswer.Explination))
        if newAnswer != answer:
            raise RuntimeError,"Something went wrong during restore"


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
            if not QuestionDB.hasQuestion(questionId):
                try:
                    text    =   tree.xpath('//div[@id="qtext_%d"]/p/text()' % questionId)[0].encode('ascii','ignore').strip() 
                    answers =   tree.xpath('//ul[@id="self_answers_%s"]/li/text()' % questionId)
                    QuestionDB.addQuestion(questionId,text,answers)
                except:
                    continue
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

            explination = tree.xpath('//textarea[@id="answer_%s_explanation"]/text()' % questionId)
            if len(explination) == 1:
                answer.Explination = explination[0]


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
    """
    def printAnswers(self):
        sys.stderr.write("[%d] Total Questiosn\n" % len(QuestionDB.getQuestionIds()))
        for questionId in QuestionDB.getQuestionIds():
            if questionId not in self.Answers:
                continue
            text        =   QuestionDB.getText(questionId)
            answers     =   QuestionDB.getAnswers(questionId)
            sys.stderr.write("[%8d] Question:   %s\n" % (questionId,text))
            for idx in range(len(answers)):
                if idx+1 == self.Answers[questionId].Selected:
                    selected = "[X]"
                else:
                    selected = "[ ]"

                if (1 << idx+1) & self.Answers[questionId].Accepted:
                    accepted = "[X]"
                else:
                    accepted = "[ ]"

                sys.stderr.write("[%8d]\t%s%s %s\n" % (questionId,selected,accepted,answers[idx]))
            sys.stderr.write("[%8d]\tImportance: %s\n" % (questionId,self.Answers[questionId].Importance))
    """
    def doAnsewr(self,question_id,selected,acceptable,importance,session):
        sys.stderr.write("Answering Question [%s]\n" % question_id)


class MatchProfile(AbstractProfile):

    def __init__(self):
        AbstractProfile.__init__(self)
        self.Answers        =   []
        self.Percentages    =   {}

    def loadFromSession(self,session,user_name):
        AbstractProfile.loadFromSession(self,session,user_name)
        link = 'http://www.okcupid.com/profile/%s' % user_name
        page = session.get(link)
        tree            =   html.fromstring(page.text)
        percentages     =   tree.xpath('//div[@id="percentages"]/span')
        for percentage in percentages:
            assert len(percentage.values()) == 1
            idx = percentage.text.find('%')
            self.Percentages[percentage.values()[0].capitalize()] = int(percentage.text[:idx])
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
        config.add_section("Percentages")
        for k,v in self.Percentages.iteritems():
            config.set("Percentages",k,"%d" % v)

    def drainConfig(self,config):
        AbstractProfile.drainConfig(self,config)
        keys = sorted(config.options("Answers"))
        for key in keys:
            self.Answers.append(int(config.get("Answers",key)))
        for (k,v) in config.items("Percentages"):
            self.Percentages[k] = int(v)

    def __fillFromLink(self,link,session):
        #sys.stderr.write("Filling From [%s]\n" % link)
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
            if not QuestionDB.hasQuestion(questionId):
                text    =   tree.xpath('//div[@id="qtext_%d"]/p/text()' % questionId)[0].encode('ascii','ignore').strip() 

                answers = tree.xpath('//form[@name="answer_%s"]/div/label[@class="radio"]/text()' % questionId)
                QuestionDB.addQuestion(questionId,text,answers)
            #----------------------------------------------------------------------------
            self.Answers.append(questionId)
            #----------------------------------------------------------------------------
        nextLink = tree.xpath('//li[@class="next"]/a/@href')
        if len(nextLink) != 0:
            return nextLink[0]
        else:
            return None
    """
    def printAnswers(self):
        sys.stderr.write("[%d] Total Questiosn\n" % len(self.Questions))
        for question in self.Questions:
            if question.Id not in self.Answers:
                continue
            sys.stderr.write("[%8d] Question:   %s\n" % (question.Id,question.Text))
            for idx in range(len(question.Answers)):
                sys.stderr.write("[%8d]\t%s\n" % (question.Id,question.Answers[idx]))
    """

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

