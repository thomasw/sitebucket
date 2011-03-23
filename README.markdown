# Sitebucket

Sitebucket is a threaded site stream monitor for the Twitter API. I highly recommend reading up on [Twitter's Site Streams API documentation](http://dev.twitter.com/pages/site_streams) before using this library.

If you don't already have beta access for the Site Streams endpoint, you'll need to [request it](https://spreadsheets.google.com/viewform?hl=en&formkey=dFBTbHZIMVhseUtqS2NkT283RTluX3c6MQ&ndplr=1#gid=0). It seems that Twitter usually responds to submissions within 2 weeks.

## Install

Sitebucket isn't in PyPI yet but, though can install it like so:

    > git clone git://github.com/thomasw/sitebucket.git
    > cd sitebucket
    > sudo python setup.py install

or if you prefer pip (<3 pip):

    > pip install -e git://github.com/thomasw/Sitebucket.git#egg=sitebucket

## Usage

First, you'll need to create oauth2 Token and Consumer objects:

    >>> import oauth2 as oauth
    >>> from sitebucket import ListenThreadMonitor
    >>> token = oauth.Token('token', 'secret')
    >>> consumer = oauth.Consumer('token', 'secret')

Next, generate a list of IDs you'd like to follow. These must be users that have authorized your app. For demonstration purposes, we'll make something up:

    >>> follow = range(1,1000)

Once you have that information ready to go, you're ready to fire up the thread
monitor:

    >>> monitor = ListenThreadMonitor(follow, consumer, token)

To run it in the current thread (be careful, it'll block forever), invoke the monitor's run method:

    >>> monitor.run() #doctest: +SKIP
    
To start a new thread, invoke the monitor's start method:

    >>> monitor.start() #doctest: +SKIP
    
The default parser will simply print all tweets any of your streaming connections receive. You'll likely want to do something other than that when you receive data. To make that happen, extend sitebucket.parser.BaseParser and pass an instance of your sub-class to the monitor when you instantiate it:

    >>> monitor = ListenThreadMonitor(follow, consumer, token, parser=MyParser()) #doctest: +SKIP

## Everything else

If you'd like to hire me, check out the [Match Strike](http://matchstrike.net/) site.

I looked to [Tweepy](http://github.com/joshthecoder/tweepy) a lot while writing this library. If you're working on something that needs to talk to Twitter, give it a go. You'll love it.

Copyright (c) 2011 [Thomas Welfley](http://welfley.me/). See [LICENSE](http://github.com/thomasw/sitebucket/blob/master/LICENSE) for details.
