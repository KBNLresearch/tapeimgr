#! /usr/bin/env python3
"""
Tapeimgr, automated reading of tape
Command-line interface

Author: Johan van der Knijff
Research department,  KB / National Library of the Netherlands
"""

import sys
import os
import imp
import time
import threading
import _thread as thread
import logging
import queue
import glob
import codecs
import argparse
from .tapeimgr import Tape
from . import config


__version__ = '0.1.0'


class tapeimgrCLI:

    def __init__(self):
        """Initiate class"""
        # Create parser
        self.parser = argparse.ArgumentParser(description='Read contents of tape. Each session is stored'
                                                          'as a separate file')
        self.finishedTape = False
        self.dirOut = os.path.expanduser("~")
        self.logFileName = config.logFileName
        self.tapeDevice = config.tapeDevice
        self.initBlockSize = config.initBlockSize
        self.sessions = ''
        self.logFile = ''
        self.prefix = config.prefix
        self.extension = config.extension
        self.fillBlocks = config.fillBlocks
        self.myTape = Tape()


    def parseCommandLine(self):
        """Parse command line"""
        # Add arguments
        self.parser.add_argument('dirOut',
                            action="store",
                            type=str,
                            help="output directory")
        self.parser.add_argument('--version', '-v',
                            action='version',
                            version=__version__)
        self.parser.add_argument('--device', '-d',
                            type=str,
                            help="non-rewind tape device",
                            action='store',
                            dest=self.tapeDevice,
                            default=self.tapeDevice)

        # Parse arguments
        self.parser.parse_args()


def printWarning(self, msg):
    """Print warning to stderr"""
    msgString = ("User warning: " + msg + "\n")
    sys.stderr.write(msgString)

def errorExit(self, msg):
    """Print warning to stderr and exit"""
    msgString = ("Error: " + msg + "\n")
    sys.stderr.write(msgString)
    sys.exit(1)

def checkFileExists(self, fileIn):
    """Check if file exists and exit if not"""
    if not os.path.isfile(fileIn):
        msg = fileIn + " does not exist"
        errorExit(msg)

def main():
    """Main command line application"""

    myCLI = tapeimgrCLI()

    # Set encoding of the terminal to UTF-8
    out = codecs.getwriter("UTF-8")(sys.stdout.buffer)
    err = codecs.getwriter("UTF-8")(sys.stderr.buffer)

    # Get input from command line
    myCLI.parseCommandLine()

    print(myCLI.tapeDevice)


if __name__ == "__main__":
    main()
