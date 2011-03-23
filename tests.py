import doctest
import unittest
import httplib

import oauth2 as oauth

from sitebucket import SiteStream

REAL_HTTPSConnection = httplib.HTTPSConnection
REAL_HTTPConnection = httplib.HTTPConnection

try:
    # Create a file called test_settings.py in the same dir as this file to 
    # override the settings in the except block below. Use the except block
    # as a template for your test_settings.py file
    # test_settings.py is in .gitignore, so it shouldn't be committed.
    from test_settings import *
except ImportError:
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
for follow_id, user_token in users:
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
        if it gets a response object with a status code other than 200.
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

class SiteStreamConnectTests(unittest.TestCase):
    def setUp(self):        
        self.stream = SiteStream(follow, consumer, token)
        self.stream.retry_time = 0
        self.stream.retry_limit = 2
    
    def test_real_http_connection(self):
        '''Establish a connection the streaming endpoint via HTTP.'''
        from sitebucket import listener
        protocol = listener.PROTOCOL
        listener.PROTOCOL = 'http://'
        httplib.HTTPSConnection = REAL_HTTPSConnection
        httplib.HTTPConnection = REAL_HTTPConnection
        resp = self.stream.connect()
        self.assertEqual(resp.status, 200)
        listener.PROTOCOL = protocol

    def test_real_https_connection(self):
        '''Establish a connection the streaming endpoint via HTTP.'''
        from sitebucket import listener
        protocol = listener.PROTOCOL
        listener.PROTOCOL = 'https://'
        httplib.HTTPSConnection = REAL_HTTPSConnection
        httplib.HTTPConnection = REAL_HTTPConnection
        resp = self.stream.connect()
        self.assertEqual(resp.status, 200)
        listener.PROTOCOL = protocol
    
    def test_timeout(self):
        '''If httplib raises a timeout exception, it should retry retry_limit
        times and then fail and return none.'''
        from socket import timeout
        httplib.HTTPSConnection = Mock_HTTPConnection(conn_exception=timeout)
        httplib.HTTPConnection = Mock_HTTPConnection(conn_exception=timeout)
        self.stream.retry_limit = 2
        resp = self.stream.connect()
        self.assertEqual(resp, None)
        self.assertEqual(self.stream.error_count, 2)
    
    def test_non_200_resp(self):
        '''If there is a non-200 response status, it should retry retry_limit
        times and then fail and return None.'''
        httplib.HTTPSConnection = Mock_HTTPConnection(status=401)
        httplib.HTTPConnection = Mock_HTTPConnection(status=401)
        self.stream.retry_limit = 2
        resp = self.stream.connect()
        self.assertEqual(resp, None)
        self.assertEqual(self.stream.error_count, 2)
    
    def test_disconnect_issued(self):
        '''If a disconnect event has been issued, the connect loop shouldn't
        even run. It should just return None. Note stream.connection will
        never be set in this case.'''
        httplib.HTTPSConnection = Mock_HTTPConnection()
        httplib.HTTPConnection = Mock_HTTPConnection()
        self.stream.disconnect()
        resp = self.stream.connect()
        self.assertEqual(resp, None)
        self.assertEqual(self.stream.connection, None)
    
    def retry_not_okay(self):
        '''If retry_ok is false, then the connection loop should immediately
        exit and return None.'''
        self.stream.error_count = self.stream.retry_limit
        resp = self.stream.connect()
        self.assertEqual(resp, None)
        self.assertEqual(self.stream.connection, None)
    
    def test_unexpected_error(self):
        '''If the connection loop encounters an unexpected error, it should
        immediately terminate.'''
        httplib.HTTPSConnection = \
            Mock_HTTPConnection(conn_exception=AttributeError)
        httplib.HTTPConnection = httplib.HTTPSConnection
        
        self.assertRaises(AttributeError, self.stream.connect)

def Mock_HTTPConnection(conn_exception=None, status=200, *args, **kwargs):
    
    def fun(*args, **kwargs):
        return MockConnection(conn_exception, status)
    
    return fun

class MockSock(object):
    def settimeout(self, *args, **kwargs):
        pass

class MockConnection(object):
    def __init__(self, conn_exception=None, status=200):
        self.sock = MockSock()
        self.getresponse_count = 0
        self.connect_count = 0
        self.conn_exception = conn_exception
        self.status = status
    
    def connect(self, *args, **kwargs):
        if self.conn_exception:
            raise self.conn_exception
    
    def request(self, *args, **kwargs):
        pass
    
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
    from sitebucket import listener, parser, thread, monitor, error, util
    from sitebucket.parser import BaseParser
    
    doc_token = oauth.Token('key', 'secret')
    doc_consumer = oauth.Consumer('key', 'secret')
    stream = listener.SiteStream([1,2,3], consumer, token)
    
    failed_stream = listener.SiteStream([1,2,3], consumer, token)
    failed_stream.error_count = 10
    failed_stream.initialized = True
    
    print "Executing doc tests:\n"
    extraglobs={'stream':stream, 'token':doc_token, 'consumer':doc_consumer, 
                'failed_stream':failed_stream}
    doctest.testmod(listener, extraglobs=extraglobs)
    doctest.testmod(parser)
    doctest.testmod(thread, extraglobs=extraglobs)
    doctest.testmod(monitor, extraglobs=extraglobs)
    doctest.testmod(error)
    doctest.testmod(util)
    print "Done!"
    
    print "\nExecuting unit tests:"
    unittest.main()
    