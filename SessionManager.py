from ProfileManager import ProfileManager
GLOBAL_SESSION  =   None

def _setSession(session):
    global GLOBAL_SESSION
    GLOBAL_SESSION  =   session

def _getSession():
    global GLOBAL_SESSION
    return GLOBAL_SESSION


class SessionManager(object):

    @staticmethod
    def doLogin(name):
        profileManager  =   ProfileManager()
        _setSession(profileManager.doLogin(name))

    @staticmethod
    def getSession():
        return _getSession()
