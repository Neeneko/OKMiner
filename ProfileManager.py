import sys
import optparse
import getpass

from Session import MinerSession
from Login import doLogin
   

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

    session = MinerSession()
    session.loadConfig()

    if options.list:
        if len(session.getProfileNames()) == 0:
            sys.stderr.write("No profiles currently stored\n")
        else:
            for profileName in session.getProfileNames():
                sys.stderr.write("Profile: %s\n" % profileName)
        sys.exit()

    userName = args[0]

    if options.add:
        if userName in session.getProfileNames():
            sys.stderr.write("Profile [%s] already stored\n")
        else:
            passWord = getpass.getpass("Enter password for [%s]:" % userName)
            session.addProfile(userName,passWord)
            session.saveConfig()
    elif options.delete:
        if userName not in session.getProfileNames():
            sys.stderr.write("Profile [%s] not already stored\n")
        else:
            session.delProfile(userName)
            session.saveConfig()
    elif options.update:
        if userName not in session.getProfileNames():
            sys.stderr.write("Profile [%s] not already stored\n")
        else:
            passWord = getpass.getpass("Enter password for [%s]:" % userName)
            session.updateProfile(userName,passWord)
            session.saveConfig()
    elif options.test:
        if userName not in session.getProfileNames():
            sys.stderr.write("Profile [%s] not present in store\n" % userName)
        elif doLogin(session,userName):
            sys.stderr.write("Profile logged in sucesfully.\n")
        else:
            sys.stderr.write("Profile login failure.\n")
