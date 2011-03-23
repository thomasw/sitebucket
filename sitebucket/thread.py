import threading

class ListenThread(threading.Thread):
    '''ListenThread is a thread object wrapper for listener.SiteStream
    objects. Instantiate a ListenThread instance with a required SiteStream
    object and then invoke the ListenThread's start method to connect
    to the stream and parse the output in a separate thread.
    
    * stream -- an instance of listener.SiteStream
    
    >>> thread = ListenThread(stream)
    >>> stream == thread.stream
    True
    
    '''
    def __init__(self, stream, *args, **kwargs):
        '''Creates a ListenThread object that can be executed by calling the
        object's start method.'''
        self.stream = stream
        super(ListenThread, self).__init__(*args, **kwargs)
        
    @property
    def connection_healthy(self):
        ''' Returns true if the thread's stream object has not yet initialized
        its connection, its connection is healthy, or it is still attempting
        to establish a connection. False if connecting failed and all 
        allotted retry attempts have been exhausted.
        
        An uninitialized connection:
        
        >>> thread = ListenThread(stream)
        >>> thread.connection_healthy
        True
        
        A stream that has failed:
        
        >>> thread = ListenThread(failed_stream)
        >>> thread.connection_healthy
        False
        
        '''
        if not self.stream.initialized:
            return True
            
        return self.stream.running and self.stream.retry_ok
    
    def restart(self):
        '''Restart resets the stream object's' failure flags and calls the
        thread's start method. Use this method to retry a connection if the
        connection_healthy property starts to return False.
        
        >>> thread = ListenThread(failed_stream)
        >>> thread.restart() #doctest: +SKIP
        
        '''
        self.stream.disconnect_issued = False
        self.stream.reset_throttles()
        self.start()
    
    def run(self):
        '''This invokes the stream object's listen method in the current
        thread. Use the object's start method to start a new thread.
        
        >>> thread = ListenThread(stream)
        >>> thread.run() #doctest: +SKIP
        
        '''
        self.stream.listen()
    
    def close(self):
        '''Sets flags in the thread's stream object that will cause its
        reading and connection loops to exit. This will eventually cause
        the thread to exit. It can be restarted via the object's restart
        method.
        
        >>> thread = ListenThread(stream)
        >>> thread.close()
        
        '''
        self.stream.disconnect()