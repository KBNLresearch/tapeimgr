#! /usr/bin/env python3
"""Shared functions module"""

import os
import logging
import subprocess as sub

def launchSubProcess(args):
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
    cmdName = args[0]
    logging.info('Command: ' + ''.join(args))
    logging.info(cmdName + 'status: ' + str(exitStatus))
    logging.info(cmdName + 'stdout:\n' + outputAsString)
    logging.info(cmdName + 'stdout:\n' + errorsAsString)

    return(exitStatus, outputAsString, errorsAsString)
