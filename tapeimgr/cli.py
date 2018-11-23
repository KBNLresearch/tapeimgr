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
        # Use formatter to control  column width
        # (see https://stackoverflow.com/a/52606755/1209004 and
        # and https://stackoverflow.com/a/5464440/1209004)
        formatter = lambda prog: argparse.HelpFormatter(prog, max_help_position=50)
        self.parser = argparse.ArgumentParser(description='Read contents of tape. Each session is'
                                              ' stored as a separate file.',
                                              formatter_class=formatter)
        self.finishedTape = False
        self.dirOut = os.path.expanduser("~")
        self.logFileName = config.logFileName
        self.tapeDevice = config.tapeDevice
        self.initBlockSize = config.initBlockSize
        self.sessions = ''
        self.logFile = ''
        self.prefix = config.prefix
        self.extension = config.extension
        self.fillBlocks = bool(config.fillBlocks)
        self.myTape = Tape()


    def parseCommandLine(self):
        """Parse command line"""

        self.parser.add_argument('dirOut',
                                 action='store',
                                 type=str,
                                 help='output directory')
        self.parser.add_argument('--version', '-v',
                                 action='version',
                                 version=__version__)
        self.parser.add_argument('--fill', '-f',
                                 action='store_true',
                                 dest='fillBlocks',
                                 default=self.fillBlocks,
                                 help='fill blocks that give read errors with null bytes')
        self.parser.add_argument('--device', '-d',
                                 action='store',
                                 type=str,
                                 help='non-rewind tape device',
                                 dest='device',
                                 default=self.tapeDevice)
        self.parser.add_argument('--blocksize', '-b',
                                 action='store',
                                 type=str,
                                 help='initial block size (must be a multiple of 512)',
                                 dest='size',
                                 default=self.initBlockSize)
        self.parser.add_argument('--sessions', '-s',
                                 action='store',
                                 type=str,
                                 help='comma-separated list of sessions to extract',
                                 dest='sessions',
                                 default=self.sessions)
        self.parser.add_argument('--prefix', '-p',
                                 action='store',
                                 type=str,
                                 help='output prefix',
                                 dest='pref',
                                 default=self.prefix)
        self.parser.add_argument('--extension', '-e',
                                 action='store',
                                 type=str,
                                 help='output file extension',
                                 dest='ext',
                                 default=self.extension)

        # Parse arguments
        args = self.parser.parse_args()
        self.dirOut = args.dirOut
        self.fillBlocks = args.fillBlocks
        self.tapeDevice = args.device
        self.initBlockSize = args.size
        self.sessions = args.sessions
        self.prefix = args.pref
        self.extension = args.ext


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
        self.errorExit(msg)

def main():
    """Main command line application"""

    myCLI = tapeimgrCLI()

    # Set encoding of the terminal to UTF-8
    out = codecs.getwriter("UTF-8")(sys.stdout.buffer)
    err = codecs.getwriter("UTF-8")(sys.stderr.buffer)

    # Get input from command line
    myCLI.parseCommandLine()

    print(myCLI.tapeDevice)
    print(myCLI.dirOut)


if __name__ == "__main__":
    main()
