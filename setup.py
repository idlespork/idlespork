#!/usr/bin/env python

from setuptools import setup

setup(name='idlespork',
      version='0.1',
      description='Improved IDLE',
      packages=['idlesporklib'],
      package_data={'idlesporklib' :
          ["Icons/*", "*.def", "*.txt", "licenses/*", "idlespork.pyw",
           "idlespork.bat"]},
      scripts=['bin/idlespork'],
     )
