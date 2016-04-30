#!/usr/bin/env python

from distutils.core import setup

long_description = open('idlesporklib/README.txt', 'r').read()

setup(name='idlespork',
      version='0.0.1',
      description='Improved IDLE',
      long_description=long_description,
      packages=['idlesporklib'],
      package_data={'idlesporklib' :
          ["Icons/*", "*.def", "*.txt", "licenses/*", "idlespork.pyw",
           "idlespork.bat"]},
      scripts=['bin/idlespork'],
      url="https://github.com/idlespork/idlespork",
      download_url="https://github.com/idlespork/idlespork/tarball/0.0.1",
      keywords=["IDLE", "background", "jobs"],
     )
