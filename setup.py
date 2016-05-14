#!/usr/bin/env python

from distutils.core import setup

long_description = open('idlesporklib/README.txt', 'r').read()
license = open('idlesporklib/licenses/LICENSE.txt', 'r').read()

setup(name='idlespork',
      version='0.1.2',
      description='idlespork is an improved version of IDLE',
      long_description=long_description,
      packages=['idlesporklib'],
      package_data={'idlesporklib' :
          ["Icons/*", "*.def", "*.txt", "licenses/*", "idlespork.pyw",
           "idlespork.bat"]},
      scripts=['bin/idlespork'],
      url="https://github.com/idlespork/idlespork",
      download_url="https://github.com/idlespork/idlespork/tarball/0.1.2",
      keywords=["IDLE", "background", "jobs"],
      author="Alon Titelman, Lior Goldberg",
      author_email="alon.ti@gmail.com, goldberg.lior@gmail.com",
      license=license,
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Environment :: Other Environment',
          'Intended Audience :: Developers',
          'Operating System :: Microsoft :: Windows',
          'Operating System :: POSIX',
          'Programming Language :: Python',
          ],
)
