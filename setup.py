#!/usr/bin/env python
from setuptools import setup, find_packages

setup(name="sitebucket",
      version="0.0.1",
      description="A threaded Twitter Site Stream consumer.",
      license="MIT",
      author="Thomas Welfley",
      author_email="info@matchstrike.net",
      url="http://github.com/thomasw/sitebucket",
      install_requires=["oauth2", "simplejson"],
      packages = find_packages(),
      keywords= "twitter sitestream site stream library consumer oauth threaded",
      zip_safe = False)
