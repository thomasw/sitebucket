'''
Sitebucket - A threaded site stream monitor for the Twitter API.
'''
import logging

from listener import SiteStream
from thread import ListenThread
from parser import DefaultParser
from monitor import ListenThreadMonitor

__version__ = '0.0.2'
__author__ = 'Thomas Welfley'
__license__ = 'MIT'

class NullHandler(logging.Handler):
    def emit(self, record):
        pass

class PrintHandler(logging.Handler):
    def emit(self, record):
        print "%s: %s" % (record.threadName, record.getMessage())

# Configure logging to do nothing.
logging.getLogger("sitebucket").addHandler(NullHandler())