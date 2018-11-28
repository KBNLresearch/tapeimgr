#! /usr/bin/env python3

"""Post-install / configuration script for tapeimgr"""

import os
import io
import json
import sys
import argparse
from shutil import copyfile


def parseCommandLine(parser):
    """Parse command line"""

    parser.add_argument('--remove', '-r',
                        action='store_true',
                        dest='removeFlag',
                        default=False,
                        help='remove all tapeimgr configuration files')
    # Parse arguments
    args = parser.parse_args()
    return args


def errorExit(msg):
    """Print error to stderr and exit"""
    msgString = ('ERROR: ' + msg + '\n')
    sys.stderr.write(msgString)
    sys.exit(1)

def infoMessage(msg):
    """Print message to stderr"""
    msgString = ('INFO: ' + msg + '\n')
    sys.stderr.write(msgString)

def writeConfigFile(sudoUser, sudoUID, sudoGID, removeFlag):
    """Create configuration file"""

    # Exit if script nor tun as root
    if sudoUID is None or sudoGID is None:
        msg = 'this script must be run as root'
        errorExit(msg)

    # Create configuration directory under /etc/
    etcDir = os.path.normpath('/etc/')

    if not os.access(etcDir, os.W_OK | os.X_OK):
        msg = 'cannot write to ' + etcDir
        errorExit(msg)

    configDir = os.path.join(etcDir, 'tapeimgr')

    if not removeFlag:
        if not os.path.isdir(configDir):
            os.mkdir(configDir)

    # Path to configuration file
    fConfig = os.path.join(configDir, 'tapeimgr.json')

    # Dictionary with items in configuration file
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

    if not removeFlag:
        # Write to configuration file in json format
        infoMessage('writing configuration file ' + fConfig)
        with io.open(fConfig, 'w', encoding='utf-8') as f:
            json.dump(configSettings, f, indent=4, sort_keys=True)
    else:
        if os.path.isfile(fConfig):
            infoMessage('removing configuration file ' + fConfig)
            os.remove(fConfig)
        if os.path.isdir(configDir):
            infoMessage('removing configuration directory ' + configDir)
            os.rmdir(configDir)

def writeDesktopFiles(packageDir, sudoUID, sudoGID, removeFlag):
    """Creates desktop files in /usr/share/applications and on desktop"""

    # Locate icon file in package
    iconFile = os.path.join(packageDir, 'icons', 'tapeimgr.png')
    if not os.path.isfile(iconFile):
        msg = 'cannot find icon file'
        errorExit(msg)

    # Locate /etc, applications and desktop directories
    desktopDir = os.path.join(os.path.join(os.path.expanduser('~')), 'Desktop')
    applicationsDir = os.path.normpath('/usr/share/applications')

    # Check if directories are writable
    if not os.access(desktopDir, os.W_OK | os.X_OK):
        msg = 'cannot write to ' + desktopDir
        errorExit(msg)

    if not os.access(applicationsDir, os.W_OK | os.X_OK):
        msg = 'cannot write to ' + applicationsDir
        errorExit(msg)

    fDesktop = os.path.join(desktopDir, 'tapeimgr.desktop')
    fApplications = os.path.join(applicationsDir, 'tapeimgr.desktop')

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
    if not removeFlag:
        try:
            infoMessage('creating desktop file ' + fDesktop)
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
            infoMessage('creating desktop file ' + fApplications)
            with io.open(fApplications, 'w', encoding='utf-8') as fA:
                for line in desktopList:
                    fA.write(line + '\n')
        except:
            msg = 'Failed to create ' + fApplications
            errorExit(msg)
    else:
        if os.path.isfile(fDesktop):
            infoMessage('removing desktop file ' + fDesktop)
            os.remove(fDesktop)
        if os.path.isfile(fApplications):
            infoMessage('removing desktop file ' + fApplications)
            os.remove(fApplications)


def  writePKPolicyFile(packageDir, removeFlag):
    """Creates policy file in /usr/share/polkit-1/actions which is required to
    launch tapeimgr with pkexec"""

    policyFileName = 'com.ubuntu.pkexec.tapeimgr.policy'

    policyFileIn = os.path.join(packageDir, 'pkexec', policyFileName)
    if not os.path.isfile(policyFileIn):
        msg = 'cannot find policy file'
        errorExit(msg)

    # Locate polkit actions dir and check if we can write there
    actionsDir = os.path.normpath('/usr/share/polkit-1/actions')
    if not os.path.isdir(actionsDir):
        msg = 'cannot find actions dir'
        errorExit(msg)

    # Construct path to output policy file
    policyFileOut = os.path.join(actionsDir, policyFileName)

    # Copy policy file to actions dir
    if not removeFlag:
        try:
            infoMessage('creating policy file ' + policyFileOut)
            copyfile(policyFileIn, policyFileOut)
        except IOError:
            msg = 'could not copy policy file to ' + policyFileOut
            errorExit(msg)
    else:
        if os.path.isfile(policyFileOut):
            infoMessage('removing policy file ' + policyFileOut)
            os.remove(policyFileOut)

def writePKLauncher(packageDir, removeFlag):
    """Creates launcher script in /usr/local/bin which is use by pkexec to
    launch tapeimgr"""

    pkExecLauncherFileName = 'tapeimgr-pkexec'

    pkExecLauncherIn = os.path.join(packageDir, 'pkexec', pkExecLauncherFileName)

    if not os.path.isfile(pkExecLauncherIn):
        msg = 'cannot find pkExec launcher file'
        errorExit(msg)

    # Locate usr/local/bin dir and check if we can write there
    binDir = os.path.normpath('/usr/local/bin')
    if not os.path.isdir(binDir):
        msg = 'cannot find ' + binDir
        errorExit(msg)

    if not os.access(binDir, os.W_OK | os.X_OK):
        msg = 'cannot write to ' + binDir
        errorExit(msg)

    # Construct path to output pk launcher
    pkExecLauncherOut = os.path.join(binDir, pkExecLauncherFileName)

    # Copy pk launcher to bin dir and make it executable
    if not removeFlag:
        try:
            infoMessage('creating pkexec launcher ' + pkExecLauncherOut)
            copyfile(pkExecLauncherIn, pkExecLauncherOut)
            os.chmod(pkExecLauncherOut, 0o755)
        except IOError:
            msg = 'could not copy pkexec launcher to ' + pkExecLauncherOut
            errorExit(msg)
    else:
        if os.path.isfile(pkExecLauncherOut):
            infoMessage('removing pkexec launcher file ' + pkExecLauncherOut)
            os.remove(pkExecLauncherOut)


def main():
    """
    Creates the following items:
    - configuration directory tapeimgr in /etc/
    - configuration file in /etc/tapeimgr
    - pkexec policy file in /usr/share/polkit-1/actions
    - pkexec launcher script in /usr/local/bin
    - desktop file in /usr/share/applications
    - desktop file on user's desktop
    If the --remove / -r switch is given the above items
    are removed (if they exist)
    """

    # Parse command line
    parser = argparse.ArgumentParser(description='tapeingr configuration tool')
    args = parseCommandLine(parser)
    removeFlag = args.removeFlag

    # Package dir
    packageDir = os.path.dirname(os.path.abspath(__file__))

    # Get evironment variables
    sudoUser = os.environ.get('SUDO_USER')
    sudoUID = os.environ.get('SUDO_UID')
    sudoGID = os.environ.get('SUDO_GID')

    writeConfigFile(sudoUser, sudoUID, sudoGID, removeFlag)
    writePKLauncher(packageDir, removeFlag)
    writePKPolicyFile(packageDir, removeFlag)
    writeDesktopFiles(packageDir, sudoUID, sudoGID, removeFlag)
    infoMessage('tapeimgr configuration completed successfully!')


if __name__ == "__main__":
    main()
