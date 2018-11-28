#! /usr/bin/env python3

"""Post-install / configuration script for tapeimgr"""

import os
import io
import json
import sys
from shutil import copyfile

def errorExit(msg):
    """Print error to stderr and exit"""
    msgString = ('ERROR: ' + msg + '\n')
    sys.stderr.write(msgString)
    sys.exit(1)

def infoMessage(msg):
    """Print message to stderr"""
    msgString = ('INFO: ' + msg + '\n')
    sys.stderr.write(msgString)

def post_install():
    """
    Creates config file + .desktop files in user directory and on desktop
    """

    sudoUser = os.environ.get('SUDO_USER')
    sudoUID = os.environ.get('SUDO_UID')
    sudoGID = os.environ.get('SUDO_GID')

    if sudoUID is None or sudoGID is None:
        msg = 'this script must be run as root'
        errorExit(msg)

    # Locate /etc, applications and desktop directories
    etcDir = os.path.normpath('/etc/')
    desktopDir = os.path.join(os.path.join(os.path.expanduser('~')), 'Desktop')
    applicationsDir = os.path.normpath('/usr/share/applications')

    # Check if directories are writable

    if not os.access(etcDir, os.W_OK | os.X_OK):
        msg = 'cannot write to ' + etcDir
        errorExit(msg)

    if not os.access(desktopDir, os.W_OK | os.X_OK):
        msg = 'cannot write to ' + desktopDir
        errorExit(msg)

    if not os.access(applicationsDir, os.W_OK | os.X_OK):
        msg = 'cannot write to ' + applicationsDir
        errorExit(msg)

    configDir = os.path.join(etcDir, 'tapeimgr')
    fDesktop = os.path.join(desktopDir, 'tapeimgr.desktop')
    fApplications = os.path.join(applicationsDir, 'tapeimgr.desktop')

    # Create configuration directory
    if not os.path.isdir(configDir):
        os.mkdir(configDir)
    fConfig = os.path.join(configDir, 'tapeimgr.json')

    # Dictionary with items in config file
    configSettings = {}
    configSettings['SUDO_USER'] = sudoUser
    configSettings['SUDO_UID'] = sudoUID
    configSettings['SUDO_GID'] = sudoGID
    configSettings['files'] = ''
    configSettings['logFileName'] = 'tapeimgr.log'
    configSettings['tapeDevice'] = '/dev/nst0'
    configSettings['initBlockSize'] = '512'
    configSettings['prefix'] = 'file'
    configSettings['extension'] = 'dd'
    configSettings['fillBlocks'] = 'False'

    # Write to config file in json format
    infoMessage('writing configuration ...')
    with io.open(fConfig, 'w', encoding='utf-8') as f:
        json.dump(configSettings, f, indent=4, sort_keys=True)

    # Locate pkexec and icon files in package dir
    packageDir = os.path.dirname(os.path.abspath(__file__))
    iconFile = os.path.join(packageDir, 'icons', 'tapeimgr.png')
    if not os.path.isfile(iconFile):
        msg = 'cannot find icon file'
        errorExit(msg)

    policyFileName = 'com.ubuntu.pkexec.tapeimgr.policy'
    pkExecLauncherFileName = 'tapeimgr-pkexec'

    policyFileIn = os.path.join(packageDir, 'pkexec', policyFileName)
    if not os.path.isfile(policyFileIn):
        msg = 'cannot find policy file'
        errorExit(msg)

    pkExecLauncherIn = os.path.join(packageDir, 'pkexec', pkExecLauncherFileName)
    if not os.path.isfile(pkExecLauncherIn):
        msg = 'cannot find pkExec launcher file'
        errorExit(msg)

    # Locate polkit actions dir and check if we can write there
    actionsDir = os.path.normpath('/usr/share/polkit-1/actions')
    if not os.path.isdir(actionsDir):
        msg = 'cannot find actions dir'
        errorExit(msg)

    # Locate usr/local/bin dir and check if we can write there
    binDir = os.path.normpath('/usr/local/bin')
    if not os.path.isdir(binDir):
        msg = 'cannot find ' + binDir
        errorExit(msg)

    if not os.access(binDir, os.W_OK | os.X_OK):
        msg = 'cannot write to ' + binDir
        errorExit(msg)

    # Construct path to output policy file
    policyFileOut = os.path.join(actionsDir, policyFileName)

    # Copy policy file to actions dir
    try:
        infoMessage('copying policy file ...')
        copyfile(policyFileIn, policyFileOut)
    except IOError:
        msg = 'could not copy policy file to ' + policyFileOut
        errorExit(msg)

    # Construct path to output pk launcher
    pkExecLauncherOut = os.path.join(binDir, pkExecLauncherFileName)

    # Copy pk launcher to bin dir and make it executable
    try:
        infoMessage('copying pkexec launcher ...')
        copyfile(pkExecLauncherIn, pkExecLauncherOut)
        os.chmod(pkExecLauncherOut, 0o755)
    except IOError:
        msg = 'could not copy pkexec launcher to ' + pkExecLauncherOut
        errorExit(msg)

    # List of desktop file lines
    desktopList = []
    desktopList.append('[Desktop Entry]')
    desktopList.append('Type=Application')
    desktopList.append('Encoding=UTF-8')
    desktopList.append('Name=tapeimgr')
    desktopList.append('Comment=Simple tape imaging and extraction tool')
    desktopList.append('Exec=tapeimgr-pkexec')
    desktopList.append('Icon=' + iconFile)
    desktopList.append('Terminal=false')
    desktopList.append('Categories=Utility;System;GTK')

    # Write desktop file to Desktop
    try:
        infoMessage('creating desktop launcher ...')
        with io.open(fDesktop, 'w', encoding='utf-8') as fD:
            for line in desktopList:
                fD.write(line + '\n')
        # Change owner to user (since script is executed as root)
        os.chown(fDesktop, int(sudoUID), int(sudoGID))
    except:
        msg = 'Failed to create ' + fDesktop
        errorExit(msg)

    # Write desktop file to applications directory
    try:
        infoMessage('creating launcher in applications directory ...')
        with io.open(fApplications, 'w', encoding='utf-8') as fA:
            for line in desktopList:
                fA.write(line + '\n')
    except:
        msg = 'Failed to create ' + fApplications
        errorExit(msg)

    infoMessage('tapeimgr configuration completed successfully!')


def main():
    """Main function"""
    post_install()


if __name__ == "__main__":
    main()
