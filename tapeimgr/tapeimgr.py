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
                 sessions,
                 prefix,
                 extension,
                 fillBlocks):
        """initialise Tape class instance"""

        # Input collected by GUI / CLI
        self.dirOut = dirOut
        self.tapeDevice = tapeDevice
        self.initBlockSize = initBlockSize
        self.sessions = sessions
        self.prefix = prefix
        self.extension = extension
        self.fillBlocks = fillBlocks
        # Input validation flags
        self.dirOutIsDirectory = False
        self.outputExistsFlag = False
        self.dirOutIsWritable = False
        self.blockSizeIsValid = False
        self.sessionsIsValid = False
        # Miscellaneous attributes
        self.tapeDeviceIOError = False
        self.successFlag = True
        self.endOfTape = False
        self.session = 1
        self.sessionsList = []
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

        # Check if initial block size is valid (i.e. a multiple of 512)
        try:
            noBlocks = (self.initBlockSize/512)

            if not noBlocks.is_integer():
                self.blockSizeIsValid = False
            elif noBlocks == 0:
                self.blockSizeIsValid = False
            else:
                self.blockSizeIsValid = True
        except ValueError:
            self.blockSizeIsValid = False

        # Check if sessions entry is valid; also split sessions string
        # to list of integers
        if self.sessions.strip() == '':
            # Empty string (default): OK
            self.sessionsIsValid = True
        else:
            try:
                # Each item in list is an integer: OK
                self.sessionsList = [int(i) for i in self.sessions.split(',')]
                self.sessionsIsValid = True
            except ValueError:
                # One or more items are not an integer
                self.sessionsIsValid = False

    def processTape(self):
        """Process a tape"""

        # Write some general info to log file
        logging.info('*** Tape extraction log ***')
        logging.info('# User input')
        logging.info('dirOut: ' + self.dirOut)
        logging.info('tapeDevice: ' + self.tapeDevice)
        logging.info('initial blockSize: ' + str(self.initBlockSize))
        logging.info('sessions: ' + self.sessions)
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
        logging.info('# Getting tape status')

        args = ['mt']
        args.append('-f')
        args.append(self.tapeDevice)
        args.append('status')
        mtStatus, mtOut, mtErr = shared.launchSubProcess(args)

        if mtStatus != 0:
            # Abort if tape device is not accessible
            self.tapeDeviceIOError = True
            self.successFlag = False
            logging.critical('# Exiting because tape device is not accessible')
            logging.info('# Success: ' + str(self.successFlag))
            # Wait 2 seconds to avoid race condition
            time.sleep(2)
            # This triggers a KeyboardInterrupt in the main thread
            thread.interrupt_main()
            sys.exit()

        # Iterate over all sessions on tape until end is detected
        while not self.endOfTape:
            # Only extract sessions defined by sessions parameter
            # (if session parameter is empty all sessions are extracted)
            if self.session in self.sessionsList or self.sessionsList == []:
                self.extractSession = True
            else:
                self.extractSession = False

            # Call session processing function
            self.processSession()

            # Increase session number
            self.session += 1

        # Create checksum file
        logging.info('# Creating checksum file')
        checksumStatus = shared.checksumDirectory(self.dirOut, self.extension)

        # Rewind and eject the tape
        logging.info('# Rewinding tape')

        args = ['mt']
        args.append('-f')
        args.append(self.tapeDevice)
        args.append('rewind')
        mtStatus, mtOut, mtErr = shared.launchSubProcess(args)

        logging.info('# Ejecting tape')

        args = ['mt']
        args.append('-f')
        args.append(self.tapeDevice)
        args.append('eject')
        mtStatus, mtOut, mtErr = shared.launchSubProcess(args)

        self.finishedTape = True

        logging.info('# Success: ' + str(self.successFlag))

        if self.successFlag:
            logging.info('# Tape processed successfully without errors')
        else:
            logging.error('# One or more errors occurred while processing tape, \
            check log file for details')

        # Wait 2 seconds to avoid race condition
        time.sleep(2)
        # This triggers a KeyboardInterrupt in the main thread
        thread.interrupt_main()

    def processSession(self):
        """Process a session"""

        if self.extractSession:
            # Determine block size for this session
            logging.info('# Establishing blockSize')
            self.findBlockSize()
            logging.info('Block size: ' + str(self.blockSize))

            # Name of output file for this session
            paddingChars = max(10 - len(self.prefix), 0)
            ofName = self.prefix + str(self.session).zfill(paddingChars) + '.' + self.extension
            ofName = os.path.join(self.dirOut, ofName)

            logging.info('# Extracting session # ' + str(self.session) + ' to file ' + ofName)

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
                logging.error('# dd encountered an error while reading the tape')

        else:
            # Fast-forward tape to next session
            logging.info('# Skipping session # ' + str(self.session) +
                         ', fast-forward to next session')

            args = ['mt']
            args.append('-f')
            args.append(self.tapeDevice)
            args.append('fsf')
            args.append('1')
            mtStatus, mtOut, mtErr = shared.launchSubProcess(args)

        # Try to position tape 1 record forward; if this fails this means
        # the end of the tape was reached
        args = ['mt']
        args.append('-f')
        args.append(self.tapeDevice)
        args.append('fsr')
        args.append('1')
        mtStatus, mtOut, mtErr = shared.launchSubProcess(args)

        if mtStatus == 0:
            # Another session exists. Position tape one record backward
            args = ['mt']
            args.append('-f')
            args.append(self.tapeDevice)
            args.append('bsr')
            args.append('1')
            mtStatus, mtOut, mtErr = shared.launchSubProcess(args)
        else:
            # No further sessions, end of tape reached
            logging.info('# Reached end of tape')
            self.endOfTape = True

    def findBlockSize(self):
        """Find block size, starting from blockSizeInit"""

        # Set blockSize to initBlockSize
        self.blockSize = self.initBlockSize
        # Flag that indicates block size was found
        blockSizeFound = False

        while not blockSizeFound:
            # Try reading 1 block from tape
            logging.info('# Guessing block size for session # ' +
                         str(self.session)  + ', trial value ' +
                         str(self.blockSize))

            args = ['dd']
            args.append('if=' + self.tapeDevice)
            args.append('of=/dev/null')
            args.append('bs=' + str(self.blockSize))
            args.append('count=1')
            ddStatus, ddOut, ddErr = shared.launchSubProcess(args)

            # Position tape 1 record backward (i.e. to the start of this session)
            args = ['mt']
            args.append('-f')
            args.append(self.tapeDevice)
            args.append('bsr')
            args.append('1')
            mtStatus, mtOut, mtErr = shared.launchSubProcess(args)

            if ddStatus == 0:
                # Block size found
                blockSizeFound = True
            else:
                # Try again with larger block size
                self.blockSize += 512
