#! /usr/bin/env python3
"""This module contains the Tape class with functions that
do the actual tape imaging.
"""

import os
import sys
import time
import logging
import _thread as thread
from . import shared

class Tape:
    """Tape class"""
    def __init__(self):
        """initialise Tape class instance"""
        # Input collected by GUI / CLI
        self.dirOut = ''
        self.tapeDevice = ''
        self.initBlockSize = 0
        self.sessions = ''
        self.prefix = ''
        self.extension = ''
        self.fillBlocks = ''
        # Miscellaneous attributes
        self.tapeDeviceIOError = False
        self.successFlag = True
        self.endOfTape = False
        self.session = 1
        self.sessionsList = []
        self.blockSize = 0

    def processTape(self,
                    dirOut,
                    tapeDevice,
                    initBlockSize,
                    sessions,
                    prefix,
                    extension,
                    fillBlocks):
        """Process a tape"""

        self.dirOut = os.path.normpath(dirOut)
        self.tapeDevice = tapeDevice
        self.initBlockSize = int(initBlockSize)
        self.sessions = sessions
        self.prefix = prefix
        self.extension = extension
        self.fillBlocks = fillBlocks

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

        if self.fillBlocks == 1:
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
            # Wait 2 seconds to avoid race condition
            time.sleep(2)
            # This triggers a KeyboardInterrupt in the main thread
            thread.interrupt_main()
            sys.exit()

        # Split sessions string to list
        try:
            self.sessionsList = [int(i) for i in self.sessions.split(',')]
        except ValueError:
            # sessions is empty string or invalid input
            self.sessionsList = []

        # Iterate over all sessions on tape until end is detected
        while not self.endOfTape:
            # Only extract sessions defined by sessions parameter
            # (if session parameter is empty all sessions are extracted)
            if self.session in self.sessionsList or self.sessionsList == []:
                self.extractSession = True
            else:
                self.extractSession = False

            # Call session processing function
            resultSession = self.processSession()

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

        # Wait 2 seconds to avoid race condition
        time.sleep(2)
        # This triggers a KeyboardInterrupt in the main thread
        thread.interrupt_main()

        return True


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

            if self.fillBlocks == 1:
                # Add conv=noerror,sync options to argument list
                args.append('conv=noerror,sync')

            ddStatus, ddOut, ddErr = shared.launchSubProcess(args)

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

        return True

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
            #mt -f "$tapeDevice" bsr 1 >> "$logFile" 2>&1
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
                print(type(self.blockSize))
                self.blockSize += 512
