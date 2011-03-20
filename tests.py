import doctest
import unittest

import tweepy
import oauth2 as oauth

from sitebucket import SiteStream

try:
    # Create a file called test_settings.py in the same dir as this file to 
    # override the settings in the except block below. Use the except block
    # as a template for your test_settings.py file
    # test_settings.py is in .gitignore, so it shouldn't be committed.
    from test_settings import *
except:
    # Consumer object for the app.
    consumer = oauth.Consumer('key', 'secret')
    
    # Token for the app owner
    token = oauth.Token('key', 'secret')

    # List of users IDs that have authorized this app and tokens.
    # IMPORTANT! The tokens will be used to tweet on behalf of the users
    # listed below.
    users = [(1, token), (2, token), (3, token), (4, token)]
    
# Generate a list of IDs based on 'users' for following with the stream.
follow = []
for follow_id, token in users:
    follow.append(follow_id)

class SiteStreamWaitLoopTests(unittest.TestCase): 
    def setUp(self):
        self.stream = SiteStream(follow, consumer, token)
        self.stream.connection = MockConnection()
    
    def test_wait_for_response(self):
        '''SiteStream.__wait_for_response should block until it returns a
        response object.
        '''
        resp = self.stream._SiteStream__wait_for_response()
        self.assertNotEqual(resp, None)
        self.assertEqual(self.stream.connection.getresponse_count, 5)
    
    def test_bad_response(self):
        '''SiteStream.__wait_for_response should immediately exit immediately
        if it gets a respone object with a status code other than 200.
        '''
        self.stream.connection.status = 401
        resp = self.stream._SiteStream__wait_for_response()
        self.assertEqual(resp, None)
    
    def test_reset_throttles_on_response(self):
        '''SiteStream.__wait_for_response should reset throttles when
        a valid response object is finally returned.
        '''
        self.stream.error_count = 10
        resp = self.stream._SiteStream__wait_for_response()
        self.assertEqual(self.stream.error_count, 0)
    
    def test_disconnect_issued(self):
        '''SiteStream.__wait_for_response should immediately exit if
        the disconnect flag has been set.
        '''
        self.stream.disconnect()
        resp = self.stream._SiteStream__wait_for_response()
        self.assertEqual(resp, None)
        self.assertEqual(self.stream.connection.getresponse_count, 0)

class MockConnection(object):
    def __init__(self):
        self.getresponse_count = 0
        self.status = 200
    
    def close(self):
        pass
    
    def getresponse(self):
        import httplib
        
        self.getresponse_count += 1
        
        if self.getresponse_count < 5:
            raise httplib.ResponseNotReady
        
        resp = MockResponseObject()
        resp.status = self.status
        
        return resp
        
class MockResponseObject(object):
    def __init__(self):
        self.read_call_count = 0
        
    def read(self, len):
        '''Returns random string data.'''
        import random
        
        rand = ''.join(random.choice(string.letters) for i in xrange(len))
        
        if random.choice((True,False)):
            rand += '\r\n'
        
        self.read_call_count += 1
        return rand

if __name__ == '__main__':
    from sitebucket import listener, parser, thread, manager, error
    from sitebucket.parser import BaseParser
    
    token = oauth.Token('key', 'secret')
    consumer = oauth.Consumer('key', 'secret')
    stream = listener.SiteStream([1,2,3], consumer, token)
    
    print "Executing doc tests:\n"
    doctest.testmod(listener, extraglobs={
        'stream':stream,
        'token':token,
        'consumer':consumer,})
    doctest.testmod(parser)
    doctest.testmod(thread)
    doctest.testmod(manager)
    doctest.testmod(error)
    print "Done!"
    
    print "\nExecuting unit tests:"
    unittest.main()
    