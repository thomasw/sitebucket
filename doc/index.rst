Sitebucket: Twitter Site Streams Consumer
=========================================

Installation
------------

Before continuing, you should make sure you have sitebucket installed. Sitebucket isn't currently listed in PyPI, though it can still be easily installed via setuptools or pip.

setuptools::

    > git clone git://github.com/thomasw/sitebucket.git
    > cd sitebucket
    > sudo python setup.py install

pip::

    > pip install -e git://github.com/thomasw/Sitebucket.git#egg=sitebucket

You'll also want to make sure that you have requested that Twitter white list your app for Site Streams access and that they have granted that request. The Site Streams API is currently in beta and you will not be able to use this library until they have granted your app access to the Site Streams endpoint.

Finally, be sure to read through Twitter's Site Streams documentation. That's it. Happy streaming!

* `Site Streams Beta Signup Form <https://spreadsheets.google.com/viewform?hl=en&formkey=dFBTbHZIMVhseUtqS2NkT283RTluX3c6MQ&ndplr=1#gid=0>`_
* `Site Streams Documetnation <http://dev.twitter.com/pages/site_streams>`_

Contents:
---------

.. toctree::
   :maxdepth: 2
   
   streams.rst
   monitor.rst
   parsing.rst
   changelog.rst
   todo.rst

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

