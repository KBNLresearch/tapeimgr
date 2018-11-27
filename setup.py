#!/usr/bin/env python
"""Setup script for tapeimgr"""

import codecs
import os
import re
from setuptools import setup, find_packages


def read(*parts):
    """Read file and return contents"""
    path = os.path.join(os.path.dirname(__file__), *parts)
    with codecs.open(path, encoding='utf-8') as fobj:
        return fobj.read()


def find_version(*file_paths):
    """Return version number from main module"""
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


INSTALL_REQUIRES = [
    'setuptools'
]
PYTHON_REQUIRES = '>=3.2'

setup(name='tapeimgr',
      packages=find_packages(),
      version=find_version('tapeimgr', 'tapeimgr.py'),
      license='Apache License 2.0',
      install_requires=INSTALL_REQUIRES,
      python_requires=PYTHON_REQUIRES,
      platforms=['linux'],
      description='Tape imager',
      long_description='Tape imager/reader; wraps around Unix dd and mt tools',
      author='Johan van der Knijff',
      author_email='johan.vanderknijff@kb.nl',
      maintainer='Johan van der Knijff',
      maintainer_email='johan.vanderknijff@kb.nl',
      url='https://github.com/KBNLresearch/tapeimgr',
      download_url=('https://github.com/KBNLresearch/tapeimgr/archive/' +
                    find_version('tapeimgr', 'tapeimgr.py') + '.tar.gz'),
      package_data={'tapeimgr': ['*.*', 'icons/*', 'pkexec/*']},
      zip_safe=False,
      entry_points={'gui_scripts': [
          'tapeimgr = tapeimgr.tapeimgr:main'],
                    'console_scripts': [
                        'tapeimgr = tapeimgr.tapeimgr:main',
                        'tapeimgr-config = tapeimgr.configure:main']},
      classifiers=[
          'Programming Language :: Python :: 3',]
     )
