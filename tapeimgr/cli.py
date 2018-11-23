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
from .tape import Tape
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

    def process(self):
        """fetch and validate entered input, and start processing"""

        # Parse command line arguments
        self.parseCommandLine()

        # Create tape instance
        self.tape = Tape(self.dirOut,
                         self.tapeDevice,
                         self.initBlockSize,
                         self.sessions,
                         self.prefix,
                         self.extension,
                         self.fillBlocks)

        # Validate input
        self.tape.validateInput()

        # Show error message and exit if any parameters didn't pass validation
        if not self.tape.dirOutIsDirectory:
            msg = ("Output directory '" + self.dirOut + "' doesn't exist!")
            errorExit(msg)

        if not self.tape.dirOutIsWritable:
            msg = ("Cannot write to directory '" + self.dirOut + "'!")
            errorExit(msg)

        if not self.tape.blockSizeIsValid:
            msg = ("--blocksize '" + str(self.initBlockSize) + "' not valid!")
            errorExit(msg)

        if not self.tape.sessionsIsValid:
            msg = ('--sessions value not valid, must be a comma-delimited\n'
                   '    string of integer numbers, or empty!')
            errorExit(msg)

        # Ask confirmation if output files exist already
        if self.tape.outputExistsFlag:
            msg = ('WARNING: writing to ' + self.dirOut + ' will overwrite existing files!\n'
                    'do you really want to proceed? (enter Y to proceed, or N to cancel): ')
            continueResponse = input(msg)

            if continueResponse.upper() == 'N':
                msg = ('Operation cancelled')
                sys.stderr.write(msg)
                sys.exit(1)
        
        # Start logger
        self.setupLogger()

        # Process the tape
        self.tape.processTape()

    def setupLogger(self):
        """Set up logger configuration"""

        # Basic configuration
        logging.basicConfig(filename=self.logFile,
                            level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')

        self.logger = logging.getLogger()

        # Add stream handler that directs logging output to stdout
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)


def printInfo(msg):
    """Print info to stderr"""
    msgString = ('INFO: ' + msg + '\n')
    sys.stderr.write(msgString)

def printWarning(msg):
    """Print warning to stderr"""
    msgString = ('WARNING: ' + msg + '\n')
    sys.stderr.write(msgString)

def errorExit(msg):
    """Print warning to stderr and exit"""
    msgString = ('ERROR: ' + msg + '\n')
    sys.stderr.write(msgString)
    sys.exit(1)


def main():
    """Main command line application"""

    # Create tapeImgrCLI instance
    myCLI = tapeimgrCLI()
    # Start main processing function
    try:
        myCLI.process()
    except KeyboardInterrupt:
        if myCLI.tape.tapeDeviceIOError:
            # Tape device not accessible
            msg = ('Cannot access tape device ' + myCLI.tape.tapeDevice +
                '. Check that device exits, and that tapeimgr is run as root')
            errorExit(msg)
        elif myCLI.tape.successFlag:
            # Tape extraction completed with no errors
            msg = ('Tape processed successfully without errors!')
            printInfo(msg)
        else:
            # Tape extraction resulted in errors
            msg = ('One or more errors occurred while processing tape, '
                    'check log file for details')
            errorExit(msg)


if __name__ == "__main__":
    main()
