#!/usr/bin/env python

from distutils.core import setup

setup(name='gestalt',
      version='0.6',
      description='gestalt Machine Control Framework',
      author='Ilan Moyer',
      author_email='imoyer@mit.edu',
      url='https://github.com/imoyer/gestalt',
      packages=['gestalt', 'gestalt.publish'],
      package_dir={'gestalt':'.'}
     )
