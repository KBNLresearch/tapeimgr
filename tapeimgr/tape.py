#! /usr/bin/env python3
"""This module contains the Tape class with functions that
do the actual tape imaging.
"""

import os
import sys
import time
import logging
import glob
import _thread as thread
from . import shared

class Tape:
    """Tape class"""
    def __init__(self,
                 dirOut,
                 tapeDevice,
                 initBlockSize,
                 files,
                 prefix,
                 extension,
                 fillBlocks,
                 logFile,
                 SUDO_UID,
                 SUDO_GID):
        """initialise Tape class instance"""

        # Input collected by GUI / CLI
        self.dirOut = dirOut
        self.tapeDevice = tapeDevice
        self.initBlockSize = initBlockSize
        self.files = files
        self.prefix = prefix
        self.extension = extension
        self.fillBlocks = fillBlocks
        self.logFile = logFile
        # Input validation flags
        self.dirOutIsDirectory = False
        self.outputExistsFlag = False
        self.deviceAccessibleFlag = False
        self.dirOutIsWritable = False
        self.blockSizeIsValid = False
        self.filesIsValid = False
        # Miscellaneous attributes
        self.SUDO_UID = SUDO_UID
        self.SUDO_GID = SUDO_GID
        self.tapeDeviceIOError = False
        self.successFlag = True
        self.endOfTape = False
        self.extractFile = False
        self.file = 1
        self.filesList = []
        self.blockSize = 0

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
            # This triggers a KeyboardInterrupt in the main thread
            thread.interrupt_main()
            sys.exit()

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
        checksumFile = os.path.join(self.dirOut, "checksums.sha512")
        shared.checksumDirectory(self.dirOut, self.extension, checksumFile)

        # Change owner to user (since script is executed as root)
        chOwnSuccess = shared.changeOwner(checksumFile,
                                          int(self.SUDO_UID),
                                          int(self.SUDO_GID))

        if not chOwnSuccess:
            logging.warning('Could not change owner settings for file ' + checksumFile)

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

        # Change owner of log file to user (since script is executed as root)
        chOwnSuccess = shared.changeOwner(self.logFile,
                                       int(self.SUDO_UID),
                                       int(self.SUDO_GID))

        if not chOwnSuccess:
            logging.warning('Could not change owner settings for file ' + self.logFile)

        # Wait 2 seconds to avoid race condition
        time.sleep(2)
        # This triggers a KeyboardInterrupt in the main thread
        thread.interrupt_main()

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

            # Change owner of extracted file to user (since script is executed as root)
            chOwnSuccess = shared.changeOwner(ofName,
                                              int(self.SUDO_UID),
                                              int(self.SUDO_GID))

            if not chOwnSuccess:
                logging.warning('Could not change owner settings for file ' + ofName)

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
