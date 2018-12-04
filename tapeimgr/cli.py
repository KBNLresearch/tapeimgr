#! /usr/bin/env python3
"""
Tapeimgr, automated reading of tape
Command-line interface

Author: Johan van der Knijff
Research department,  KB / National Library of the Netherlands
"""

import sys
import logging
import argparse
from .tape import Tape
from . import config


class tapeimgrCLI:

    """This class defines the command line interface + associated functions
    for associated actions
    """

    def __init__(self):
        """Initiate class"""
        # Create parser
        # Use formatter to control  column width
        # (see https://stackoverflow.com/a/52606755/1209004 and
        # and https://stackoverflow.com/a/5464440/1209004)
        formatter = lambda prog: argparse.HelpFormatter(prog, max_help_position=50)
        self.parser = argparse.ArgumentParser(description='Read contents of tape. Each file'
                                              ' on the tape is stored as a separate file.',
                                              formatter_class=formatter)

        # Logging stuff
        self.logger = logging.getLogger()
        # Add stream handler that directs logging output to stdout
        self.consoleHandler = logging.StreamHandler(sys.stdout)
        # Create tape instance
        self.tape = Tape()
        # Read configuration file
        self.tape.getConfiguration()


    def parseCommandLine(self):
        """Parse command line"""

        self.parser.add_argument('dirOut',
                                 action='store',
                                 type=str,
                                 help='output directory')
        self.parser.add_argument('--version', '-v',
                                 action='version',
                                 version=config.version)
        self.parser.add_argument('--fill', '-f',
                                 action='store_true',
                                 dest='fillBlocks',
                                 default=self.tape.fillBlocks,
                                 help='fill blocks that give read errors with null bytes')
        self.parser.add_argument('--device', '-d',
                                 action='store',
                                 type=str,
                                 help='non-rewind tape device',
                                 dest='device',
                                 default=self.tape.tapeDevice)
        self.parser.add_argument('--blocksize', '-b',
                                 action='store',
                                 type=str,
                                 help='initial block size (must be a multiple of 512)',
                                 dest='size',
                                 default=self.tape.initBlockSize)
        self.parser.add_argument('--files', '-s',
                                 action='store',
                                 type=str,
                                 help='comma-separated list of files to extract',
                                 dest='files',
                                 default=self.tape.files)
        self.parser.add_argument('--prefix', '-p',
                                 action='store',
                                 type=str,
                                 help='output prefix',
                                 dest='pref',
                                 default=self.tape.prefix)
        self.parser.add_argument('--extension', '-e',
                                 action='store',
                                 type=str,
                                 help='output file extension',
                                 dest='ext',
                                 default=self.tape.extension)

        # Parse arguments
        args = self.parser.parse_args()
        self.tape.dirOut = args.dirOut
        self.tape.fillBlocks = args.fillBlocks
        self.tape.tapeDevice = args.device
        self.tape.initBlockSize = args.size
        self.tape.files = args.files
        self.tape.prefix = args.pref
        self.tape.extension = args.ext

    def process(self):
        """fetch and validate entered input, and start processing"""

        # Read configuration file
        self.tape.getConfiguration()

        if not self.tape.configSuccess:
            msg = ("Error reading configuration file! \n" +
                   "Run '(sudo) tapeimgr-config' to fix this.")
            errorExit(msg)

        # Parse command line arguments
        self.parseCommandLine()

        # Validate input
        self.tape.validateInput()

        # Show error message and exit if any parameters didn't pass validation
        if not self.tape.dirOutIsDirectory:
            msg = ("Output directory '" + self.tape.dirOut + "' doesn't exist!")
            errorExit(msg)

        if not self.tape.dirOutIsWritable:
            msg = ("Cannot write to directory '" + self.tape.dirOut + "'!")
            errorExit(msg)

        if not self.tape.deviceAccessibleFlag:
            msg = ('Tape device is not accessible!')
            errorExit(msg)

        if not self.tape.blockSizeIsValid:
            msg = ("--blocksize '" + str(self.tape.initBlockSize) + "' not valid!")
            errorExit(msg)

        if not self.tape.filesIsValid:
            msg = ('--files value not valid, must be a comma-delimited\n'
                   '    string of integer numbers, or empty!')
            errorExit(msg)

        # Ask confirmation if output files exist already
        if self.tape.outputExistsFlag:
            msg = ('WARNING: writing to ' + self.tape.dirOut + ' will overwrite existing files!\n'
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
        logging.basicConfig(filename=self.tape.logFile,
                            level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')

        # Console handler configuration
        self.consoleHandler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        self.consoleHandler.setFormatter(formatter)
        self.logger.addHandler(self.consoleHandler)


def printInfo(msg):
    """Print info to stderr"""
    msgString = ('INFO: ' + msg + '\n')
    sys.stderr.write(msgString)


def printWarning(msg):
    """Print warning to stderr"""
    msgString = ('WARNING: ' + msg + '\n')
    sys.stderr.write(msgString)


def errorExit(msg):
    """Print error to stderr and exit"""
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
        if myCLI.tape.finishedFlag:
            if myCLI.tape.tapeDeviceIOError:
                # Tape device not accessible
                msg = ('Cannot access tape device ' + myCLI.tape.tapeDevice +
                       '. Check that device exists, and that current user has permission ' +
                       'to access it')
                errorExit(msg)
            elif myCLI.tape.successFlag:
                # Tape extraction completed with no errors
                msg = ('Tape processed successfully without errors!')
                printInfo(msg)
                sys.exit(0)
            else:
                # Tape extraction resulted in errors
                msg = ('One or more errors occurred while processing tape, '
                       'check log file for details')
                errorExit(msg)
    except Exception as e:
        # Unexpected error
        msg = 'An unexpected error occurred, see log file for details'
        logging.error(str(e))
        errorExit(msg)

if __name__ == "__main__":
    main()
