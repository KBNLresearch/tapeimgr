#! /usr/bin/env python
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
try:
    import thread  # Python 2.x
except ImportError:
    import _thread as thread  # Python 3.x


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
    allFiles = glob.glob(directory + "/*")

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


def worker():
    # Skeleton worker function, runs in separate thread (see below)   
    print("worker started")
    while True:
        # Report time / date at 2-second intervals
        time.sleep(2)
        timeStr = time.asctime()
        msg = 'Current time: ' + timeStr
        logging.info(msg) 


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
