#! /usr/bin/env python3
"""Shared functions module"""

import os
import logging
import glob
import hashlib
import subprocess as sub


def launchSubProcess(args, writeLog=True):
    """Launch subprocess and return exit code, stdout and stderr"""
    try:
        # Execute command line; stdout + stderr redirected to objects
        # 'output' and 'errors'.
        # Setting shell=True avoids console window poppong up with pythonw
        # BUT shell=True is not working with argument lists,
        # see https://stackoverflow.com/a/26417712/1209004
        p = sub.Popen(args, stdout=sub.PIPE, stderr=sub.PIPE, shell=False)
        output, errors = p.communicate()

        # Decode to UTF8
        outputAsString = output.decode('utf-8')
        errorsAsString = errors.decode('utf-8')

        exitStatus = p.returncode

    except Exception:
        # I don't even want to to start thinking how one might end up here ...

        exitStatus = -99
        outputAsString = ""
        errorsAsString = ""

    # Logging
    if writeLog:
        cmdName = args[0]
        logging.info('Command: ' + ' '.join(args))

        if exitStatus == 0:
            logging.info(cmdName + ' status: ' + str(exitStatus))
            logging.info(cmdName + ' stdout:\n' + outputAsString)
            logging.info(cmdName + ' stderr:\n' + errorsAsString)
        else:
            logging.error(cmdName + ' status: ' + str(exitStatus))
            logging.error(cmdName + ' stdout:\n' + outputAsString)
            logging.error(cmdName + ' stderr:\n' + errorsAsString)

    return(exitStatus, outputAsString, errorsAsString)


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


def checksumDirectory(directory, extension, checksumFile):
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
        fChecksum = open(checksumFile, "w", encoding="utf-8")
        for fName in checksums:
            lineOut = checksums[fName] + " " + os.path.basename(fName) + '\n'
            fChecksum.write(lineOut)
        fChecksum.close()
        wroteChecksums = True
    except IOError:
        wroteChecksums = False

    return wroteChecksums
