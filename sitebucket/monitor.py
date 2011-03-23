import threading
import collections
import time
import logging

from listener import SiteStream, FOLLOW_LIMIT
from thread import ListenThread
from util import grouper
from parser import DefaultParser

logger = logging.getLogger("sitebucket")

NONFULL_STREAM_LIMIT = 10
RESTART_DEAD_STREAMS = True
MONITOR_SLEEP_INTERVAL = 10
CONSOLIDATE_SLEEP_INTERVAL = 30

class ListenThreadMonitor(threading.Thread):
    '''The ListenThreadMonitor takes a follow list of any size, creates
    ListenThread objects and corresponding SiteStream objects for the follow
    list and initializes them. By default, the monitor will attempt to restart
    any connections that fail.
    
    The monitor's run method blocks, so invoke it via start method if you want
    to run it in a separate thread.
    
    To use, first import ListenThreadMonitor and oauth2
    
    >>> from sitebucket import ListenThreadMonitor
    >>> import oauth2
    
    Then generate your Consumer and Token objects:
    >>> token = oauth2.Token('key', 'secret')
    >>> consumer = oauth2.Consumer('key', 'secret')
    
    And then instantiate your ListenThreadMonitor object.
    >>> monitor = ListenThreadMonitor([1,2,3], consumer, token)
    
    Calling run will start the streaming connections and block until you kill
    the process.
    >>> monitor.run() #doctest: +SKIP
    
    Calling start will start the monitor loop in a separate thread.
    >>> monitor.start() #doctest: +SKIP
    
    It can be killed later via the disconnect method:
    >>> monitor.disconnect()
    
    '''
    def __init__(self, follow, consumer, token, stream_with="user",
                 parser=DefaultParser(), *args, **kwargs):
        '''Returns a ListenThreadMonitor object. Parameters are identical to
        the SiteStream object.
        
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
        
        '''
        # Make sure follow is iterable.
        if not isinstance(follow, collections.Iterable):
            follow = [follow]
        follow.sort()
        
        self.follow = follow
        self.consumer = consumer
        self.token = token
        self.stream_with = stream_with
        self.parser = parser
        self.threads = self.__create_thread_objects(follow, stream_with)
        self.disconnect_issued = False
        self.running = False
        
        super(ListenThreadMonitor, self).__init__(*args, **kwargs)
    
    def __create_thread_objects(self, follow, stream_with):
        '''Split the specified follow list into groups of CONNECTION_LIMIT
        or smaller and then create ListenThread objects for those groups.
        
        >>> follow = range(1,1001)
        >>> monitor = ListenThreadMonitor(follow, consumer, token)
        >>> len(monitor.threads) >= len(follow)/FOLLOW_LIMIT
        True
        
        '''
        threads = []
        chunks = list(grouper(FOLLOW_LIMIT, follow))
        
        for follow in chunks:
            stream = SiteStream(follow, self.consumer, self.token,
                                stream_with, self.parser)
            thread = ListenThread(stream)
            thread.daemon = True
            threads.append(thread)
        
        logger.debug("Created %s new thread objects." % len(threads))
        return threads
    
    def run(self):
        '''Starts all threads and begins monitoring loop. Invoke this via
        the object's start method to run the monitor in a separate thread.
        
        >>> monitor = ListenThreadMonitor([1, 2, 3], consumer, token)
        >>> monitor.run() #doctest: +SKIP
        
        '''
        if not self.disconnect_issued:
            logger.info("Starting threads...")
            [thread.start() for thread in self.threads]
        
        while not self.disconnect_issued:
            self.running = True
            
            if RESTART_DEAD_STREAMS:
                self.restart_unhealthy_streams()
            
            if len(self.nonfull_streams) > NONFULL_STREAM_LIMIT:
                self.consolidate_streams()
            
            if self.disconnect_issued:
                logger.info("Disconnect issued. Issuing shutdown requests to streams...")
                while self.threads:
                    thread = self.threads.pop()
                    thread.close()
                logger.info("Monitor terminating...")
            else:
                time.sleep(MONITOR_SLEEP_INTERVAL)
            
        self.running = False
    
    def add_follows(self, follow, start=True):
        '''Creates and adds new ListenThreads based on a specified follow
        list. Optionally starts the new threads.
        
        * follow -- list of users to start following
        * start -- (default: True) If true, start running the new threads.
        
        >>> follow = range(1,FOLLOW_LIMIT*10+1)
        >>> monitor = ListenThreadMonitor([], consumer, token)
        >>> monitor.add_follows(follow, start=False)
        >>> len(monitor.threads) >= len(follow)/FOLLOW_LIMIT
        True
        
        '''
        threads = self.__create_thread_objects(follow, self.stream_with)
        
        if start:
            [thread.start() for thread in threads]
        
        self.threads.extend(threads)
        
    def consolidate_streams(self):
        '''Find all streams that aren't following the maximum number of users
        they are permitted to follow and consolidate them into the smallest
        number of streaming connections possible.
        
        >>> monitor = ListenThreadMonitor([], consumer, token)
        >>> monitor.add_follows([1,], start=False)
        >>> monitor.add_follows([2,], start=False)
        >>> monitor.add_follows([3,], start=False)
        >>> len(monitor.threads)
        3
        >>> monitor.consolidate_streams()
        >>> len(monitor.threads)
        1
        '''
        logger.info("Attempting to minimize active stream connections.")
        nonfull_streams = self.nonfull_streams
        # Create a list of all the users in nonfull_streams
        follow = []
        [follow.extend(x.stream.follow) for x in nonfull_streams]
        
        consolidated_threads = \
            self.__create_thread_objects(follow, self.stream_with)
        
        # We only need to do work if our set of consolidated threads is
        # actually smaller than what we have currently
        if len(consolidated_threads) >= len(nonfull_streams):
            return
        
        if self.running:
            [x.start() for x in consolidated_threads]
        
        # Sleep after starting up the new threads to give them time to
        # catch up.
        # TODO: What we really need to do here is start the new threads
        # and wait for them to start receiving duplicate data
        # (The best way to do this is to wrap the stream's parsers with
        # some sort of object that keeps track of that. )
        time.sleep(CONSOLIDATE_SLEEP_INTERVAL)
        
        # Remove the old threads from the thread list and disconnect them.
        for x in nonfull_streams:
            self.threads.remove(x)
            x.close()
            
        # Add the new threads to the thread list
        logger.info("Reduced stream connections by %s" \
            % (len(nonfull_streams) - len(consolidated_threads)))
        self.threads.extend(consolidated_threads)
        
        
    def restart_unhealthy_streams(self):
        '''Restart all unhealthy streaming ListenThreads.'''
        if len(self.unhealthy_streams) > 0:
            logger.info('%s unhealthy streams detected.' \
                % len(self.unhealthy_streams))
        [thread.restart() for thread in self.unhealthy_streams]
    
    def disconnect(self):
        '''Sets the disconnect flag to True, which will cause the monitor's
        loop to terminate.
        
        >>> monitor = ListenThreadMonitor([], consumer, token)
        >>> monitor.disconnect()
        >>> monitor.run()
        
        '''
        logger.debug("Disconnect received.")
        self.disconnect_issued = True
    
    @property
    def nonfull_streams(self):
        ''' Returns a list of threads that aren't following a number of users
        equal to FOLLOW_LIMIT.
        
        >>> follow = range(1,FOLLOW_LIMIT+2)
        >>> monitor = ListenThreadMonitor(follow, consumer, token)
        >>> len(monitor.nonfull_streams) == 1
        True
        
        '''
        return [x for x in self.threads \
                if len(x.stream.follow) < NONFULL_STREAM_LIMIT]
    
    @property
    def healthy_streams(self):
        ''' Returns a list of all threads that are healthy, uninitialized,
        or connecting.
        
        >>> monitor = ListenThreadMonitor([1], consumer, token)
        >>> len(monitor.healthy_streams) == 1
        True
        
        '''
        return [x for x in self.threads if x.connection_healthy]
    
    @property
    def unhealthy_streams(self):
        '''Returns a list of all threads with failed connections.
        
        >>> monitor = ListenThreadMonitor([], consumer, token)
        >>> monitor.unhealthy_streams
        []
        
        >>> failed_thread = ListenThread(failed_stream)
        >>> monitor.threads.append(failed_thread)
        >>> monitor.unhealthy_streams[0] == failed_thread
        True
        
        '''
        return [x for x in self.threads if x.connection_healthy == False]