#! /usr/bin/env python3
"""This module contains iromlab's cdWorker code, i.e. the code that monitors
the list of jobs (submitted from the GUI) and does the actual imaging and ripping
"""

import sys
import os
import shutil
import time
import glob
import csv
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


def checksumDirectory(directory):
    """Calculate checksums for all files in directory"""

    # All files in directory
    allFiles = glob.glob(directory + "/*." + config.extension)

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

def processTape():
    """Process a tape"""
    # TODO: add actual calls to mt

    print("entering processTape")

    # Write some general info to log file
    logging.info('*** Tape extraction log ***')
    #dateStart="$(date)"
    #logging.info('# Start date/time ' + dateStart)
    logging.info('# User input')
    logging.info('dirOut = ' + config.dirOut)
    logging.info('tapeDevice = ' + config.tapeDevice) 
    logging.info('initial blockSize = ' + config.initBlocksize)
    logging.info('sessions = ' + config.sessions)
    logging.info('prefix = ' + config.prefix)
    logging.info('extension = ' + config.extension)
    logging.info('fill blocks = ' + str(config.fillBlocks))

    if config.fillBlocks == 1:
        # dd's conv=sync flag results in padding bytes for each block if block 
        # size is too large, so override user-defined value with default
        # if -f flag was used
        config.initBlocksize = 512
        logging.info('Reset initial block size to 512 because -f flag is used')

    # Flag that indicates end of tape was reached
    endOfTape = False
    # Session index
    session = 1
    
    # Get tape status, output to log file
    logging.info('# Tape status')
    # TODO insert mt call
    # mt -f "$tapeDevice" status | tee -a "$logFile"

    # Split sessions string to list
    try:
        sessions = [int(i) for i in config.sessions.split(',')]
    except ValueError:
        # config.sessions is empty string or invalid input
        sessions = []

    # Iterate over all sessions on tape until end is detected
    # TODO remove session < 10 limit
    while not endOfTape and session < 10:
        print("session = " + str(session))
        # Only extract sessions defined by sessions parameter
        # (if session parameter is empty all sessions are extracted)
        if session in sessions or sessions == []:
            extractSession = True
        else:
            extractSession = False

        print("xtractSession = " + str(extractSession))

        # Call session processing function 
        resultSession = processSession(session, extractSession)
        print("Processing session")

        # Increase session number
        session += 1
    
    # Create checksum file
    logging.info('# Creating checksum file')
    checksumStatus = checksumDirectory(os.path.normpath(config.dirOut))
        
    # Rewind and eject the tape
    logging.info('# Rewinding tape')
    #mt -f "$tapeDevice" rewind 2>&1 | tee -a "$logFile"
    logging.info('# Ejecting tape')
    #mt -f "$tapeDevice" eject 2>&1 | tee -a "$logFile"

    # Write end date/time to log
    #dateEnd="$(date)"
    #logging.info('# End date/time ' + dateEnd)
    return True


def processSession(sessionNumber, extractSessionFlag):
    """Process a session"""
    # TODO: add actual calls to mt and dd

    if extractSessionFlag:
        # Determine block size for this session
        blockSize = findBlocksize(config.initBlocksize)
        logging.info('# Block size = ' + str(blockSize))

        # Name of output file for this session
        ofName = config.prefix + str(sessionNumber).zfill(6) + '.' + config.extension
        ofName = os.path.join(config.dirOut, ofName)
        #ofName = "$dirOut"/""$prefix""`printf "%06g" "$session"`."$extension"

        logging.info('# Extracting session #' + str(sessionNumber) + ' to file ' + ofName)

        if config.fillBlocks == 1:
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
        #echo "# Skipping session # ""$session"", fast-forward to next session" | tee -a "$logFile"
        #mt -f "$tapeDevice" fsf 1 >> "$logFile" 2>&1

    """
    # Try to position tape 1 record forward; if this fails this means
    # the end of the tape was reached
    mt -f "$tapeDevice" fsr 1 >> "$logFile" 2>&1
    mtStatus="$?"
    echo "# mt exit code = " "$mtStatus" | tee -a "$logFile"

    if [[ "$mtStatus" -eq 0 ]]; then
        # Another session exists. Position tape one record backward
        mt -f "$tapeDevice" bsr 1 >> "$logFile" 2>&1
    else
        # No further sessions, end of tape reached
        echo "# Reached end of tape" | tee -a "$logFile"
        endOfTape="true"
    fi
    """
    return True

def findBlocksize(blockSizeInit):
    """Find block size, starting from blockSizeInit"""
    blockSize = 9999
    return blockSize

def worker():
    # Skeleton worker function, runs in separate thread (see below)   

    # Loop periodically scans value of config.readyToStart
    while not config.readyToStart:
        time.sleep(2)

    msg = 'Time to wake up'
    logging.info(msg) 

    time.sleep(2)
    timeStr = time.asctime()
    msg = 'Current time: ' + timeStr
    logging.info(msg)

    # Process the tape
    resultTape = processTape()

    config.finishedTape = True
    print("Worker finished!")
    
    # Wait 2 seconds to avoid race condition
    time.sleep(2)
    # This triggers a KeyboardInterrupt in the main thread
    thread.interrupt_main()


def processDiscTest(carrierData):
    """Dummy version of processDisc function that doesn't do any actual imaging
    used for testing only
    """
    jobID = carrierData['jobID']
    logging.info(''.join(['### Job identifier: ', jobID]))
    logging.info(''.join(['PPN: ', carrierData['PPN']]))
    logging.info(''.join(['Title: ', carrierData['title']]))
    logging.info(''.join(['Volume number: ', carrierData['volumeNo']]))

    # Create dummy carrierInfo dictionary (values are needed for batch manifest)
    carrierInfo = {}
    carrierInfo['containsAudio'] = False
    carrierInfo['containsData'] = False
    carrierInfo['cdExtra'] = False

    success = True

    # Create comma-delimited batch manifest entry for this carrier

    # Dummy value for VolumeIdentifier
    volumeID = 'DUMMY'

    # Put all items for batch manifest entry in a list

    rowBatchManifest = ([jobID,
                         carrierData['PPN'],
                         carrierData['volumeNo'],
                         carrierData['carrierType'],
                         carrierData['title'],
                         volumeID,
                         str(success),
                         str(carrierInfo['containsAudio']),
                         str(carrierInfo['containsData']),
                         str(carrierInfo['cdExtra'])])

    # Note: carrierType is value entered by user, NOT auto-detected value! Might need some changes.

    # Open batch manifest in append mode
    if sys.version.startswith('3'):
        # Py3: csv.reader expects file opened in text mode
        bm = open(config.batchManifest, "a", encoding="utf-8")
    elif sys.version.startswith('2'):
        # Py2: csv.reader expects file opened in binary mode
        bm = open(config.batchManifest, "ab")

    # Create CSV writer object
    csvBm = csv.writer(bm, lineterminator='\n')

    # Write row to batch manifest and close file
    csvBm.writerow(rowBatchManifest)
    bm.close()

    return success


def quitIromlab():
    """Send KeyboardInterrupt after user pressed Exit button"""
    logging.info('*** Quitting because user pressed Exit ***')
    # Wait 2 seconds to avoid race condition between logging and KeyboardInterrupt
    time.sleep(2)
    # This triggers a KeyboardInterrupt in the main thread
    thread.interrupt_main()


def cdWorker():
    """Worker function that monitors the job queue and processes the discs in FIFO order"""

    # Initialise 'success' flag to prevent run-time error in case user
    # finalizes batch before entering any carriers (edge case)
    success = True

    """
    # Loop periodically scans value of config.batchFolder
    while not config.readyToStart:
        time.sleep(2)

    logging.info(''.join(['batchFolder set to ', config.batchFolder]))

    # Define batch manifest (CSV file with minimal metadata on each carrier)
    config.batchManifest = os.path.join(config.batchFolder, 'manifest.csv')

    # Write header row if batch manifest doesn't exist already
    if not os.path.isfile(config.batchManifest):
        headerBatchManifest = (['jobID',
                                'PPN',
                                'volumeNo',
                                'carrierType',
                                'title',
                                'volumeID',
                                'success',
                                'containsAudio',
                                'containsData',
                                'cdExtra'])

        # Open batch manifest in append mode
        if sys.version.startswith('3'):
            # Py3: csv.reader expects file opened in text mode
            bm = open(config.batchManifest, "a", encoding="utf-8")
        elif sys.version.startswith('2'):
            # Py2: csv.reader expects file opened in binary mode
            bm = open(config.batchManifest, "ab")

        # Create CSV writer object
        csvBm = csv.writer(bm, lineterminator='\n')

        # Write header to batch manifest and close file
        csvBm.writerow(headerBatchManifest)
        bm.close()
    """
    # Initialise batch
    logging.info('*** Initialising batch ***')
 
    # Flag that marks end of batch (main processing loop keeps running while False)
    endOfBatchFlag = False

    # Check if user pressed Exit, and quit if so ...
    if config.quitFlag:
        quitIromlab()

    while not endOfBatchFlag and not config.quitFlag:
        time.sleep(2)
        logging.info('*** Writing an entry ***')
        """
        # Get directory listing, sorted by creation time
        # List conversion because in Py3 a filter object is not a list!
        files = list(filter(os.path.isfile, glob.glob(config.jobsFolder + '/*')))
        files.sort(key=lambda x: os.path.getctime(x))

        noFiles = len(files)

        if noFiles > 0:
            # Identify oldest job file
            jobOldest = files[0]

            # Open job file and read contents

            if sys.version.startswith('3'):
                # Py3: csv.reader expects file opened in text mode
                fj = open(jobOldest, "r", encoding="utf-8")
            elif sys.version.startswith('2'):
                # Py2: csv.reader expects file opened in binary mode
                fj = open(jobOldest, "rb")

            fjCSV = csv.reader(fj)
            jobList = next(fjCSV)
            fj.close()

            if jobList[0] == 'EOB':
                # End of current batch
                endOfBatchFlag = True
                config.readyToStart = False
                config.finishedBatch = True
                os.remove(jobOldest)
                shutil.rmtree(config.jobsFolder)
                shutil.rmtree(config.jobsFailedFolder)
                logging.info('*** End Of Batch job found, closing batch ***')
                # Wait 2 seconds to avoid race condition between logging and KeyboardInterrupt
                time.sleep(2)
                # This triggers a KeyboardInterrupt in the main thread
                thread.interrupt_main()
            else:
                # Set up dictionary that holds carrier data
                carrierData = {}
                carrierData['jobID'] = jobList[0]
                carrierData['PPN'] = jobList[1]
                carrierData['title'] = jobList[2]
                carrierData['volumeNo'] = jobList[3]
                carrierData['carrierType'] = jobList[4]

                # Process the carrier
                #success = processDisc(carrierData)
                success = processDiscTest(carrierData)

            if success and not endOfBatchFlag:
                # Remove job file
                os.remove(jobOldest)
            elif not endOfBatchFlag:
                # Move job file to failed jobs folder
                baseName = os.path.basename(jobOldest)
                os.rename(jobOldest, os.path.join(config.jobsFailedFolder, baseName))

        """

        # Check if user pressed Exit, and quit if so ...
        if config.quitFlag:
            quitIromlab()
