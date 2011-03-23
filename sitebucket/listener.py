import httplib
from socket import timeout
import urllib
import time
import collections
import oauth2 as oauth
import simplejson as json

from parser import DefaultParser, BaseParser
from error import SitebucketError


PROTOCOL = 'http://'
SITE_STREAM_HOST = 'betastream.twitter.com'
URI = '/2b/site.json'
TIMEOUT = 40.0
RETRY_LIMIT = 10
RETRY_TIME = 2.0
METHOD = 'GET'

ALLOWED_STREAM_WITH = ('user', 'followings')
FOLLOW_LIMIT = 100


class SiteStream(object):
    ''' The SiteStream object establishes an authenticated OAuth Connection
    to Twitter's site stream endpoint and parses the returned data.'''
    def __init__(self, follow, consumer, token, stream_with="user",
                 parser=DefaultParser()):
        '''Returns a SiteStream object.
            
        Keyword arguments:
        
        * follow -- a list of users that have authenticated your app to follow
        * stream_with -- 'user' or 'followings'. A value of 'user' will cause 
        the stream to only return data about actions the users specified in
        follow take. A value of 'followings' will cause the Stream object to
        return data about the user's followings (basically their home
        timeline). This defaults to 'user'.
        * consumer -- a python-oauth2 Consumer object for the app
        * token -- a python-oauth2 Token object for the app's owner account.
        * parser -- an object that extends BaseParser that will handle data
        returned by the stream.
        
        To use, first import SiteStream and oauth2
        
        >>> from sitebucket import SiteStream
        >>> import oauth2
        
        Then generate your Consumer and Token objects:
        >>> token = oauth2.Token('key', 'secret')
        >>> consumer = oauth2.Consumer('key', 'secret')
        
        And then instantiate your SiteStream object.
        >>> stream = SiteStream([1,2,3], consumer, token)
            
        '''
        # Make sure follow is iterable.
        if not isinstance(follow, collections.Iterable):
            follow = [follow]
        
        follow.sort()
        self.follow = follow
        self.stream_with = stream_with
        self.consumer = consumer
        self.token = token
        self.host = SITE_STREAM_HOST
        self.parser = parser
        
        self.running = False
        self.disconnect_issued = False
        self.initialized = False
        self._last_request = None
        self.connection = None
        self.reset_throttles()
        
        self.__check_params()
    
    @property
    def url(self):
        ''' Returns the URL based on PROTOCOL, SITE_STREAM_HOST, and URI.
        
        >>> stream = SiteStream([1,2], consumer, token)
        >>> stream.url
        'http://betastream.twitter.com/2b/site.json'
        
        '''
        return "%s%s%s" % (PROTOCOL, SITE_STREAM_HOST, URI)
    
    @property
    def request(self):
        ''' Returns an oauth2 request object to be used for connecting to the
        streaming API endpoint. For debugging purposes, the returned request
        object is cached in __last_request.
            
        >>> req = stream.request
        >>> print req.to_url() #doctest: +ELLIPSIS
        http://betastream.twitter.com/2b/site.json?...
        
        '''
        parameters = {
            'oauth_version': "1.0",
            'oauth_nonce': oauth.generate_nonce(),
            'oauth_timestamp': int(time.time()),
            'follow': ','.join(map(str, self.follow)),
            'with': self.stream_with,
            'oauth_token': self.token.key,
            'oauth_consumer_key': self.consumer.key
        }
        request = oauth.Request(METHOD, self.url, parameters=parameters)
        request.sign_request(
            oauth.SignatureMethod_HMAC_SHA1(), self.consumer, self.token)
        
        self._last_request = request
        return request
    
    @property
    def retry_ok(self):
        '''Returns True or False based on whether or not this SiteStream 
        object has exceeded re-connection limits.
        
        >>> stream.retry_ok
        True
        >>> stream.error_count = stream.retry_limit # Raise error count to max
        >>> stream.retry_ok
        False
        
        '''
        return self.error_count < self.retry_limit
    
    def __check_params(self):
        ''' Raises an exception if the init parameters are invalid.
        
        >>> SiteStream(range(1, FOLLOW_LIMIT+2), consumer, token) #doctest: +ELLIPSIS
        Traceback (most recent call last):
          ...
        SitebucketError: The number of followers specified (...) exceeds the follow limit: ....
        
        >>> SiteStream(1, consumer, token, stream_with='family')
        Traceback (most recent call last):
          ...
        SitebucketError: 'family' is an invalid value for stream_with.
        
        >>> SiteStream(1, consumer, token, parser=[])
        Traceback (most recent call last):
          ...
        SitebucketError: parser must extend BaseParser.
        
        >>> SiteStream(1, ('key', 'secret'), token,)
        Traceback (most recent call last):
          ...
        SitebucketError: Expecting python-oauth2 Consumer object for consumer.
        >>> SiteStream(1, consumer, ('key', 'secret'),)
        Traceback (most recent call last):
          ...
        SitebucketError: Expecting python-oauth2 Token object for token.
        
        '''
        if not self.stream_with in ALLOWED_STREAM_WITH:
            raise SitebucketError("'%s' is an invalid value for stream_with."
                                  % self.stream_with)
        
        if len(self.follow) > FOLLOW_LIMIT:
            raise SitebucketError('The number of followers specified (%s) exceeds the follow limit: %s.'
                                   % (len(self.follow), FOLLOW_LIMIT))
        
        if not isinstance(self.parser,BaseParser):
            raise SitebucketError('parser must extend BaseParser.')
        
        if not isinstance(self.consumer, oauth.Consumer):
            raise SitebucketError('Expecting python-oauth2 Consumer object for consumer.')
        
        if not isinstance(self.token, oauth.Token):
            raise SitebucketError('Expecting python-oauth2 Token object for token.')
    
    def __wait_for_response(self):
        ''' Invokes self.connection's getresponse() method and locks execution
        until the response object is ready and has a 200 response status.
        
        If the response has a status other than 200, the method logs the error
        and returns None.
        
        '''
        ready = False
        resp = None
        
        while not ready and not self.disconnect_issued:
            try:
                resp = self.connection.getresponse()
                ready = True
                if resp.status != 200:
                    print "Error: %s" % resp.status
                    resp = None
                    break
                else:
                    print "Connection established."
                    self.running = True
                    self.reset_throttles()
            except httplib.ResponseNotReady:
                ready = False
                self.sleep(
                    stime=.1,
                    update_error_count=False,
                    close_connection=False)
            except:
                raise
        
        return resp
        
    def listen(self):
        ''' listen initiates a streaming connection via the connect method and
        processes data from Twitter as it is received.
        
        Important: This method blocks until the connection fails or another
        thread sets flags that causes the read loop to terminate.
        
        >>> stream.listen() #doctest: +SKIP
        
        '''
        if not self.running:
            resp = self.connect()
        
        while self.running and not self.disconnect_issued and resp \
              and not resp.isclosed() and self.retry_ok:
            try:
                data = ''
                while not self.disconnect_issued:
                    data += resp.read(1)
                    if data.endswith('\r\n'):
                        self.on_receive(data)
                        data = ''
            except timeout:
                print "Timeout!"
                self.sleep()
                break
            except AttributeError:
                if not self.disconnect_issued:
                    self.sleep(stime=0)
                    raise
            except:
                self.sleep(stime=0)
                raise
        
        if self.disconnect_issued:
            print "Exiting read loop."
            return None
        
        return self.listen()
        
    def connect(self):
        ''' Repeatedly attempts to connect to the streaming server until
        either the failure conditions are met or a successful connection
        is made. Returns None (in the event of a disconnect request or error)
        or an httplib response object.
        
        >>> stream.connect() #doctest: +SKIP
        
        '''
        while not self.running and self.retry_ok and not self.disconnect_issued:
            try:
                if PROTOCOL == "http://":
                    self.connection = httplib.HTTPConnection(self.host)
                else:
                    self.connection = httplib.HTTPSConnection(self.host)
                self.connection.connect()
                self.connection.sock.settimeout(self.timeout)
                self.connection.request('GET', self.request.to_url())
                resp = self.__wait_for_response()
                
                if resp:
                    break
            except timeout:
                print "Timeout!"
            except Exception, exception:
                self.sleep(stime=0)
                raise exception 
            
            if not self.disconnect_issued:
                self.sleep()
        
        if not self.retry_ok:
            print "Failed to connect."
            resp = None
        
        if self.disconnect_issued:
            print "Aborting connection attempt."
            resp = None
        
        return resp
    
    def reset_throttles(self):
        ''' Resets all stream throttles, flags, and buffers to their default
        value. This can be used to prepare a SiteStream object for a 
        reconnection attempt or to clear error states after a successful
        connection is made.
        
        >>> stream.error_count = RETRY_LIMIT # Error count at limit
        >>> stream.retry_time = 10000.0 # really high retry time
        >>> stream.buffer = 'leftover input' # buffer with unfinished input
        >>> stream.reset_throttles() # reset!
        >>> stream.retry_limit == RETRY_LIMIT \
        and stream.retry_time == RETRY_TIME and stream.error_count == 0 \
        and stream.timeout == TIMEOUT and stream.buffer == ''
        True
        
        '''
        self.retry_limit = RETRY_LIMIT
        self.retry_time = RETRY_TIME
        self.error_count = 0
        self.timeout = TIMEOUT
        self.buffer = ''
    
    def sleep(self, stime=None, update_error_count=True,
              close_connection=True):
        ''' Causes the the thread to sleep for the amount of time specified
        in the stream's retry_time property. The retry_time is then squared.
        This method may optionally increment the error_count property and
        terminate the connection.
        
        * stime -- sleep time that overrides the object's retry_time property.
        If this is set, retry_time is not squared.
        * update_error_count -- if this is true, the method increments the 
        error_count property
        * close_connection -- if this is true, the method terminates the 
        connection.
        
        >>> old_error_count = stream.error_count
        >>> stream.sleep(0)
        >>> stream.error_count > old_error_count
        True
        
        '''
        
        self.running = False
        
        if update_error_count:
            self.error_count += 1
        
        if close_connection and self.connection:
            self.connection.close()
        
        if stime is None:
            print "Sleeping for %s" % self.retry_time
            time.sleep(self.retry_time)
            self.retry_time *= self.retry_time
        else:
            time.sleep(stime)
            
    def disconnect(self):
        ''' This method sets flags that will cause the stream processing loops
        to terminate. However, since the listen method blocks, this method
        will need to be called from another thread to terminate the
        connection if listen is still running.
        
        >>> stream.disconnect()
        >>> stream.disconnect_issued
        True
        >>> stream.running
        False
        
        '''
        self.disconnect_issued = True
        self.sleep(stime=0, update_error_count=False, close_connection=True)
    
    def on_receive(self, data):
        ''' When a complete message is received from the stream
        (json terminated by \r\n), on_receive passes the data to the parser
        object's parse method and clears the buffer.
        
        If we have a custom parser defined like so:
        
        >>> class myparser(BaseParser):
        ...     def parse(self, data):
        ...         print data.strip()
        
        and we tell our stream object to use this parser, it will simply print
        the data anytime it is received from the stream.
        
        >>> stream.parser = myparser()
        >>> stream.on_receive("{'some':'json'}\\r\\n")
        {'some':'json'}
        
        '''
        self.buffer += data
        if data.endswith("\r\n") and self.buffer.strip():
            self.parser.parse(self.buffer)
            self.buffer = ''
