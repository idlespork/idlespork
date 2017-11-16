#!/usr/bin/env python

from distutils.core import setup

long_description = open('idlesporklib/README.txt', 'r').read()

try:
    from distutils.command.bdist_msi import bdist_msi
    from msilib import add_data

    class build_msi(bdist_msi):
        def run(self):
            bdist_msi.run(self)
            add_data(self.db, 'Shortcut', [('DesktopShortcut', 'DesktopFolder',
                'idlespork', 'Scripts', r'[TARGETDIR]\pythonw.exe',
                r'"[Scripts]\idlespork"', None, None, None, None, None, None)])
            self.db.Commit()
except ImportError:
    build_msi = None

setup(name='idlespork',
      version='0.1.3',
      description='idlespork is an improved version of IDLE',
      long_description=long_description,
      packages=['idlesporklib'],
      package_data={'idlesporklib' :
          ['Icons/*', '*.def', '*.txt', 'licenses/*', 'idlespork.pyw',
           'idlespork.bat']},
      scripts=['bin/idlespork'],
      url='https://github.com/idlespork/idlespork',
      download_url='https://github.com/idlespork/idlespork/tarball/0.1.3',
      keywords=['IDLE', 'background', 'jobs'],
      author='Alon Titelman, Lior Goldberg',
      author_email='alon.ti@gmail.com, goldberg.lior@gmail.com',
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Environment :: Other Environment',
          'Intended Audience :: Developers',
          'Operating System :: Microsoft :: Windows',
          'Operating System :: POSIX',
          'Programming Language :: Python',
          ],
      cmdclass = { 'bdist_msi' : build_msi },
      options = { 'bdist_msi' : { 'target_version' : '2.7' } },
)
