#! /usr/bin/env python3
"""
Tapeimgr, automated reading of tapes

Author: Johan van der Knijff
Research department,  KB / National Library of the Netherlands
"""
import sys
from .cli import main as cliLaunch
from .gui import main as guiLaunch
from . import config

__version__ = '0.3.0'

def main():
    """Launch GUI if no command line arguments were given; otherwise launch CLI"""
    config.version = __version__
    noArgs = len(sys.argv)
    if noArgs == 1:
        guiLaunch()
    else:
        cliLaunch()

main()
