import sys
import os
import optparse
import getpass
import base64
import ConfigParser
import requests
  
class ProfileManager(object):

    def __init__(self):
        self.__configPath   =   os.path.join(os.path.dirname(sys.modules[__name__].__file__), "Config")
        self.__config       =   ConfigParser.ConfigParser()
        self.__config.optionxform=str
        self.__configName   =   os.path.join(self.__configPath,"config.ini")
        if not os.path.exists(self.__configPath):
            sys.stderr.write("Config path does not exist, creating\n")
            os.mkdir(self.__configPath)
        if not os.path.exists(self.__configName):
            sys.stderr.write("Config file does not exist, creating\n")
            self.__config.add_section("Profiles")
            self.saveConfig()

        self.__config.read(self.__configName)

    def saveConfig(self):
        with open(self.__configName,'wb') as configFile:
            self.__config.write(configFile)

    def getProfileNames(self):
        return [ x for (x,_) in self.__config.items("Profiles") ]

    def addProfile(self,user_name,pass_word):
        self.__config.set("Profiles",user_name,base64.b64encode(pass_word))
        self.saveConfig()

    def updateProfile(self,user_name,pass_word):
        self.addProfile(user_name,pass_word)
        self.saveConfig()

    def delProfile(self,user_name):
        self.__config.remove_option("Profiles",user_name)
        self.saveConfig()

    def getPassword(self,user_name):
        return base64.b64decode(self.__config.get("Profiles",user_name))

    def doLogin(self,user_name):
        session     =   requests.Session()
        pass_word   =   self.getPassword(user_name)

        credentials = {'username': user_name, 'password': pass_word, 'dest': '/home'}
        resp = session.post('https://www.okcupid.com/login', data=credentials)
        if resp.url == u'https://www.okcupid.com/login':
            return None
        elif resp.url == u'http://www.okcupid.com/home':
            return session
        else:
            raise RuntimeError,"Unexpected login redirect to [%s]" % resp.url


if __name__ == "__main__":
    usage = "usage: %prog [options] username"
    parser = optparse.OptionParser()
    parser.add_option('-l','--list',help="List currently stored usernames",action="store_true",default=False)
    parser.add_option('-a','--add',help="Add a username and password",action="store_true",default=False)
    parser.add_option('-u','--update',help="Update a username with a new password",action="store_true",default=False)
    parser.add_option('-d','--delete',help="Delete a stored username and password",action="store_true",default=False)
    parser.add_option('-t','--test',help="Test login for a specified username",action="store_true",default=False)
    options, args = parser.parse_args()

    if not options.list ^ options.add ^ options.delete ^ options.test ^ options.update: 
        sys.stderr.write("Please select between list, add, delete, or test\n")
        sys.exit()

    if not (options.list or options.add or options.delete or options.test or options.update):
        sys.stderr.write("Please select between list, add, delete, or test\n");
        sys.exit()

    if (options.add or options.delete or options.test or options.update) and len(args) != 1:
        sys.stderr.write("Please supply username\n")
        sys.exit()       

    profileManager  =   ProfileManager()

    if options.list:
        if len(profileManager.getProfileNames()) == 0:
            sys.stderr.write("No profiles currently stored\n")
        else:
            for profileName in profileManager.getProfileNames():
                sys.stderr.write("Profile: %s\n" % profileName)
        sys.exit()

    userName = args[0]

    if options.add:
        if userName in profileManager.getProfileNames():
            sys.stderr.write("Profile [%s] already stored\n")
        else:
            passWord = getpass.getpass("Enter password for [%s]:" % userName)
            profileManager.addProfile(userName,passWord)
    elif options.delete:
        if userName not in profileManager.getProfileNames():
            sys.stderr.write("Profile [%s] not already stored\n")
        else:
            profileManager.delProfile(userName)
    elif options.update:
        if userName not in profileManager.getProfileNames():
            sys.stderr.write("Profile [%s] not already stored\n")
        else:
            passWord = getpass.getpass("Enter password for [%s]:" % userName)
            profileManager.updateProfile(userName,passWord)
    elif options.test:
       
        if userName not in profileManager.getProfileNames():
            sys.stderr.write("Profile [%s] not present in store\n" % userName)
        elif profileManager.doLogin(userName) is not None:
            sys.stderr.write("Profile logged in sucesfully.\n")
        else:
            sys.stderr.write("Profile login failure.\n")
