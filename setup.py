#!/usr/bin/env python

from distutils.core import setup

setup(name='idlespork',
      version='0.1',
      description='Improved IDLE',
      packages=['idlesporklib'],
      package_data={'idlesporklib' : ["Icons/*", "*.def", "*.txt", "licenses/*"]}
     )
