#! /usr/bin/env python3
"""This module contains the Tape class with functions that
do the actual tape imaging.
"""

import os
import io
import json
import time
import logging
import glob
from . import shared

class Tape:
    """Tape class"""
    def __init__(self):
        """initialise Tape class instance"""

        # Input collected by GUI / CLI
        self.dirOut = os.path.expanduser("~")
        self.tapeDevice = ''
        self.initBlockSize = ''
        self.files = ''
        self.prefix = ''
        self.extension = ''
        self.fillBlocks = ''
        # Input validation flags
        self.dirOutIsDirectory = False
        self.outputExistsFlag = False
        self.deviceAccessibleFlag = False
        self.dirOutIsWritable = False
        self.blockSizeIsValid = False
        self.filesIsValid = False
        # Config file location, depends on package directory
        packageDir = os.path.dirname(os.path.abspath(__file__))
        homeDir = os.path.normpath(os.path.expanduser("~"))
        if packageDir.startswith(homeDir):
            self.configFile = os.path.join(homeDir, '.config/tapeimgr/tapeimgr.json')
        else:
            self.configFile = os.path.normpath('/etc/tapeimgr/tapeimgr.json')
        # Miscellaneous attributes
        self.logFile = ''
        self.logFileName = ''
        self.checksumFileName = ''
        self.initBlockSizeDefault = ''
        self.finishedFlag = False
        self.tapeDeviceIOError = False
        self.successFlag = True
        self.configSuccess = True
        self.endOfTape = False
        self.extractFile = False
        self.file = 1
        self.filesList = []
        self.blockSize = 0

    def getConfiguration(self):
        """read configuration file and set variables accordingly"""
        if not os.path.isfile(self.configFile):
            self.configSuccess = False

        # Read config file to dictionary
        try:
            with io.open(self.configFile, 'r', encoding='utf-8') as f:
                configDict = json.load(f)
        except:
            self.configSuccess = False

        if self.configSuccess:
            # Update class variables
            try:
                self.files = configDict['files']
                self.logFileName = configDict['logFileName']
                self.checksumFileName = configDict['checksumFileName']
                self.tapeDevice = configDict['tapeDevice']
                self.initBlockSize = configDict['initBlockSize']
                self.initBlockSizeDefault = self.initBlockSize
                self.prefix = configDict['prefix']
                self.extension = configDict['extension']
                self.fillBlocks = bool(configDict['fillBlocks'])
            except KeyError:
                self.configSuccess = False


    def validateInput(self):
        """Validate and pre-process input"""

        # Check if dirOut is a directory
        self.dirOutIsDirectory = os.path.isdir(self.dirOut)

        # Check if glob pattern for dirOut, prefix and extension matches existing files
        if glob.glob(self.dirOut + '/' + self.prefix + '*.' + self.extension):
            self.outputExistsFlag = True

        # Check if dirOut is writable
        self.dirOutIsWritable = os.access(self.dirOut, os.W_OK | os.X_OK)

        # Check if tape device is accessible
        args = ['mt']
        args.append('-f')
        args.append(self.tapeDevice)
        args.append('status')
        mtStatus, mtOut, mtErr = shared.launchSubProcess(args, False)

        if mtStatus == 0:
            self.deviceAccessibleFlag = True

        # Check if initial block size is valid (i.e. a multiple of 512)
        try:
            self.initBlockSize = int(self.initBlockSize)

            noBlocks = (self.initBlockSize/512)

            if not noBlocks.is_integer():
                self.blockSizeIsValid = False
            elif noBlocks == 0:
                self.blockSizeIsValid = False
            else:
                self.blockSizeIsValid = True
        except ValueError:
            self.blockSizeIsValid = False

        # Check if files entry is valid; also split files string
        # to list of integers
        if self.files.strip() == '':
            # Empty string (default): OK
            self.filesIsValid = True
        else:
            try:
                # Each item in list is an integer: OK
                self.filesList = [int(i) for i in self.files.split(',')]
                self.filesIsValid = True
            except ValueError:
                # One or more items are not an integer
                self.filesIsValid = False

        # Convert fillBlocks to Boolean
        self.fillBlocks = bool(self.fillBlocks)

        # Log file
        self.logFile = os.path.join(self.dirOut, self.logFileName)

    def processTape(self):
        """Process a tape"""

        # Write some general info to log file
        logging.info('***************************')
        logging.info('*** TAPE EXTRACTION LOG ***')
        logging.info('***************************\n')
        logging.info('*** USER INPUT ***')
        logging.info('dirOut: ' + self.dirOut)
        logging.info('tapeDevice: ' + self.tapeDevice)
        logging.info('initial blockSize: ' + str(self.initBlockSize))
        logging.info('files: ' + self.files)
        logging.info('prefix: ' + self.prefix)
        logging.info('extension: ' + self.extension)
        logging.info('fill blocks: ' + str(self.fillBlocks))

        if self.fillBlocks:
            # dd's conv=sync flag results in padding bytes for each block if block
            # size is too large, so override user-defined value with default
            # if -f flag was used
            self.initBlockSize = 512
            logging.info('Reset initial block size to 512 because -f flag is used')

        # Get tape status, output to log file
        logging.info('*** Getting tape status ***')

        args = ['mt']
        args.append('-f')
        args.append(self.tapeDevice)
        args.append('status')
        mtStatus, mtOut, mtErr = shared.launchSubProcess(args)

        if mtStatus != 0:
            # Abort if tape device is not accessible
            self.tapeDeviceIOError = True
            self.successFlag = False
            logging.critical('Exiting because tape device is not accessible')
            logging.info('Success: ' + str(self.successFlag))

            # Wait 2 seconds to avoid race condition
            time.sleep(2)

            # Set finishedFlag
            self.finishedFlag = True


        # Iterate over all files on tape until end is detected
        while not self.endOfTape:
            # Only extract files defined by files parameter
            # (if file parameter is empty all files are extracted)
            if self.file in self.filesList or self.filesList == []:
                self.extractFile = True
            else:
                self.extractFile = False

            # Call file processing function
            self.processFile()

            # Increase file number
            self.file += 1

        # Create checksum file
        logging.info('*** Creating checksum file ***')
        checksumFile = os.path.join(self.dirOut, self.checksumFileName)
        shared.checksumDirectory(self.dirOut, self.extension, checksumFile)

        # Rewind and eject the tape
        logging.info('*** Rewinding tape ***')

        args = ['mt']
        args.append('-f')
        args.append(self.tapeDevice)
        args.append('rewind')
        mtStatus, mtOut, mtErr = shared.launchSubProcess(args)

        logging.info('*** Ejecting tape ***')

        args = ['mt']
        args.append('-f')
        args.append(self.tapeDevice)
        args.append('eject')
        mtStatus, mtOut, mtErr = shared.launchSubProcess(args)

        logging.info('Success: ' + str(self.successFlag))

        if self.successFlag:
            logging.info('Tape processed successfully without errors')
        else:
            logging.error('One or more errors occurred while processing tape, \
            check log file for details')

        # Set finishedFlag
        self.finishedFlag = True

        # Wait 2 seconds to avoid race condition
        time.sleep(2)

    def processFile(self):
        """Process a file"""

        if self.extractFile:
            # Determine block size for this file
            logging.info('*** Establishing blockSize ***')
            self.findBlockSize()
            logging.info('Block size: ' + str(self.blockSize))

            # Name of output file for this file
            paddingChars = max(10 - len(self.prefix), 0)
            ofName = self.prefix + str(self.file).zfill(paddingChars) + '.' + self.extension
            ofName = os.path.join(self.dirOut, ofName)

            logging.info('*** Extracting file # ' + str(self.file) + ' to file ' + ofName + ' ***')

            args = ['dd']
            args.append('if=' + self.tapeDevice)
            args.append('of='+ ofName)
            args.append('bs=' + str(self.blockSize))

            if self.fillBlocks:
                # Add conv=noerror,sync options to argument list
                args.append('conv=noerror,sync')

            ddStatus, ddOut, ddErr = shared.launchSubProcess(args)

            if ddStatus != 0:
                self.successFlag = False
                logging.error('dd encountered an error while reading the tape')

        else:
            # Fast-forward tape to next file
            logging.info('*** Skipping file # ' + str(self.file) +
                         ', fast-forward to next file ***')

            args = ['mt']
            args.append('-f')
            args.append(self.tapeDevice)
            args.append('fsf')
            args.append('1')
            mtStatus, mtOut, mtErr = shared.launchSubProcess(args, False)

        # Try to position tape 1 record forward; if this fails this means
        # the end of the tape was reached
        args = ['mt']
        args.append('-f')
        args.append(self.tapeDevice)
        args.append('fsr')
        args.append('1')
        mtStatus, mtOut, mtErr = shared.launchSubProcess(args, False)

        if mtStatus == 0:
            # Another file exists. Position tape one record backward
            args = ['mt']
            args.append('-f')
            args.append(self.tapeDevice)
            args.append('bsr')
            args.append('1')
            mtStatus, mtOut, mtErr = shared.launchSubProcess(args, False)
        else:
            # No further files, end of tape reached
            logging.info('*** Reached end of tape ***')
            self.endOfTape = True

    def findBlockSize(self):
        """Find block size, starting from blockSizeInit"""

        # Set blockSize to initBlockSize
        self.blockSize = self.initBlockSize
        # Flag that indicates block size was found
        blockSizeFound = False

        while not blockSizeFound:
            # Try reading 1 block from tape
            logging.info('*** Guessing block size for file # ' +
                         str(self.file)  + ', trial value ' +
                         str(self.blockSize) + ' ***')

            args = ['dd']
            args.append('if=' + self.tapeDevice)
            args.append('of=/dev/null')
            args.append('bs=' + str(self.blockSize))
            args.append('count=1')
            ddStatus, ddOut, ddErr = shared.launchSubProcess(args, False)

            # Position tape 1 record backward (i.e. to the start of this file)
            args = ['mt']
            args.append('-f')
            args.append(self.tapeDevice)
            args.append('bsr')
            args.append('1')
            mtStatus, mtOut, mtErr = shared.launchSubProcess(args, False)

            if ddStatus == 0:
                # Block size found
                blockSizeFound = True
            else:
                # Try again with larger block size
                self.blockSize += 512
