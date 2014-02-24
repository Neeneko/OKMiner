import requests

def doLogin(session,user_name):
    """
    @TODO - so what do errors look like?
    """
    session.setSession(requests.Session())
 
    credentials = {'username': user_name, 'password': session.getPassword(user_name), 'dest': '/home'}
    resp = session.getSession().post('https://www.okcupid.com/login', data=credentials)

    if resp.url == u'https://www.okcupid.com/login':
        return False
    elif resp.url == u'http://www.okcupid.com/home':
        return True
    else:
        raise RuntimeError,"Unexpected login redirect to [%s]" % resp.url

def doConnectWithoutLogin(session):
    session.setSession(requests.Session())
