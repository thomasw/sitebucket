import simplejson as json

class BaseParser(object):
    '''BaseParser is a prototype for Stream Parser objects. All parsers should
    extend this class.'''
    
    def parse(self, token):
        '''This method must be overridden. It raises a NotImplementedError.
        '''
        raise NotImplementedError
    
class DefaultParser(BaseParser):
    '''A simple Stream parser that converts the returned data to JSON and
    prints tweets. '''
    
    def parse(self, token):
        ''' Converts input data to JSON and calls the tweet method if the 
        input is a tweet.
        
        Input that isn't a tweet:
        
        >>> parser = DefaultParser()
        >>> parser.parse('{"some":"json"}')
        
        Input that would be considered a tweet:
        
        >>> parser.parse('{"for_user":1, "message":{"text":"hi!"}}')
        For user 1: hi!
        
        '''
        content = json.loads(token)
        
        if 'message' in content and 'text' in content['message']:
            self.tweet(content['for_user'], content['message'])
    
    def tweet(self, for_user, tweet):
        ''' Prints a tweet based on a tweet message and who the user is for.
        
        * for_user -- the id of the user the tweet is for.
        * tweet -- a dictionary containing a 'text' entry
        
        >>> parser = DefaultParser()
        >>> parser.tweet(1, {'text':'hi!'})
        For user 1: hi!
        
        '''
        print "For user %s: %s" % (for_user, tweet['text'])