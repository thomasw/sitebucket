import doctest
import unittest

import tweepy
import oauth2 as oauth

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
    