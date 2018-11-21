#! /usr/bin/env python3
"""This module contains iromlab's cdWorker code, i.e. the code that monitors
the list of jobs (submitted from the GUI) and does the actual imaging and ripping
"""

import os
import time
import glob
import hashlib
import logging
import _thread as thread
from . import shared
from . import config

def generate_file_sha512(fileIn):
    """Generate sha512 hash of file"""

    # fileIn is read in chunks to ensure it will work with (very) large files as well
    # Adapted from: http://stackoverflow.com/a/1131255/1209004

    blocksize = 2**20
    m = hashlib.sha512()
    with open(fileIn, "rb") as f:
        while True:
            buf = f.read(blocksize)
            if not buf:
                break
            m.update(buf)
    return m.hexdigest()


def checksumDirectory(directory, extension):
    """Calculate checksums for all files in directory"""

    # All files in directory
    allFiles = glob.glob(directory + "/*." + extension)

    # Dictionary for storing results
    checksums = {}

    for fName in allFiles:
        hashString = generate_file_sha512(fName)
        checksums[fName] = hashString

    # Write checksum file
    try:
        fChecksum = open(os.path.join(directory, "checksums.sha512"), "w", encoding="utf-8")
        for fName in checksums:
            lineOut = checksums[fName] + " " + os.path.basename(fName) + '\n'
            fChecksum.write(lineOut)
        fChecksum.close()
        wroteChecksums = True
    except IOError:
        wroteChecksums = False

    return wroteChecksums

class Tape:
    """Batch class"""
    def __init__(self):
        """initialise Tape class instance"""
        # Input collected by GUI / CLI
        self.dirOut = ''
        self.tapeDevice = ''
        self.initBlocksize = ''
        self.prefix = ''
        self.extension = ''
        self.fillBlocks = ''
        # Flag that indicates end of tape was reached
        self.endOfTape = False
        # Session index
        self.session = 1
        self.sessionsList = []

    def processTape(self,
                    dirOut,
                    tapeDevice,
                    initBlocksize,
                    sessions,
                    prefix,
                    extension,
                    fillBlocks):
        """Process a tape"""
        # TODO: add actual calls to mt

        print("entering processTape")

        self.dirOut = os.path.normpath(dirOut)
        self.tapeDevice = tapeDevice
        self.initBlocksize = initBlocksize
        self.sessions = sessions
        self.prefix = prefix
        self.extension = extension
        self.fillBlocks = fillBlocks

        # Write some general info to log file
        logging.info('*** Tape extraction log ***')
        logging.info('# User input')
        logging.info('dirOut = ' + self.dirOut)
        logging.info('tapeDevice = ' + self.tapeDevice)
        logging.info('initial blockSize = ' + self.initBlocksize)
        logging.info('sessions = ' + self.sessions)
        logging.info('prefix = ' + self.prefix)
        logging.info('extension = ' + self.extension)
        logging.info('fill blocks = ' + str(self.fillBlocks))

        if self.fillBlocks == 1:
            # dd's conv=sync flag results in padding bytes for each block if block
            # size is too large, so override user-defined value with default
            # if -f flag was used
            self.initBlocksize = 512
            logging.info('Reset initial block size to 512 because -f flag is used')

        # Get tape status, output to log file
        logging.info('# Tape status')
        # TODO insert mt call
        # mt -f "$tapeDevice" status | tee -a "$logFile"

        # Split sessions string to list
        try:
            self.sessionsList = [int(i) for i in self.sessions.split(',')]
        except ValueError:
            # sessions is empty string or invalid input
            self.sessionsList = []

        # Iterate over all sessions on tape until end is detected
        # TODO remove session < 10 limit
        while not self.endOfTape and self.session < 10:
            print("session = " + str(self.session))
            # Only extract sessions defined by sessions parameter
            # (if session parameter is empty all sessions are extracted)
            if self.session in self.sessionsList or self.sessionsList == []:
                self.extractSession = True
            else:
                self.extractSession = False

            print("extractSession = " + str(self.extractSession))

            # Call session processing function
            resultSession = self.processSession()
            print("Processing session")

            # Increase session number
            self.session += 1

        # Create checksum file
        logging.info('# Creating checksum file')
        checksumStatus = checksumDirectory(self.dirOut, self.extension)

        # Rewind and eject the tape
        logging.info('# Rewinding tape')
        #mt -f "$tapeDevice" rewind 2>&1 | tee -a "$logFile"
        logging.info('# Ejecting tape')
        #mt -f "$tapeDevice" eject 2>&1 | tee -a "$logFile"

        # Write end date/time to log
        #dateEnd="$(date)"
        #logging.info('# End date/time ' + dateEnd)

        self.finishedTape = True

        # Wait 2 seconds to avoid race condition
        time.sleep(2)
        # This triggers a KeyboardInterrupt in the main thread
        thread.interrupt_main()

        return True


    def processSession(self):
        """Process a session"""
        # TODO: add actual calls to mt and dd

        if self.extractSession:
            # Determine block size for this session
            self.blockSize = self.findBlocksize()
            logging.info('Block size = ' + str(self.blockSize))

            # Name of output file for this session
            ofName = self.prefix + str(self.session).zfill(6) + '.' + self.extension
            ofName = os.path.join(self.dirOut, ofName)
            #ofName = "$dirOut"/""$prefix""`printf "%06g" "$session"`."$extension"

            logging.info('# Extracting session # ' + str(self.session) + ' to file ' + ofName)

            if self.fillBlocks == 1:
                # Invoke dd with conv=noerror,sync options
                pass
                #dd if="$tapeDevice" of="$ofName" bs="$bSize" conv=noerror,sync >> "$logFile" 2>&1
            else:
                pass
                #dd if="$tapeDevice" of="$ofName" bs="$bSize" >> "$logFile" 2>&1

            #ddStatus="$?"
            #echo "# dd exit code = " "$ddStatus" | tee -a "$logFile"
        else:
            # Fast-forward tape to next session
            pass
            logging.info('# Skipping session # ' + str(self.session) + ', fast-forward to next session')
            #mt -f "$tapeDevice" fsf 1 >> "$logFile" 2>&1

        # Try to position tape 1 record forward; if this fails this means
        # the end of the tape was reached
        #mt -f "$tapeDevice" fsr 1 >> "$logFile" 2>&1
        mtStatus = 0 # TODO, change to actual status!
        logging.info('mt exit code = ' + str(mtStatus))

        if mtStatus == 0:
            # Another session exists. Position tape one record backward
            #mt -f "$tapeDevice" bsr 1 >> "$logFile" 2>&1
            pass
        else:
            # No further sessions, end of tape reached
            logging.info('# Reached end of tape')
            self.endOfTape = True

        return True

    def findBlocksize(self):
        """Find block size, starting from blockSizeInit"""
        self.blockSize = 9999
        return self.blockSize