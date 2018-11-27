#! /usr/bin/env python3

"""Post-install / configuration script for tapeimgr"""

import os
import io
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
    Creates .desktop files in user directory and on desktop
    """

    uid = os.environ.get('SUDO_UID')
    gid = os.environ.get('SUDO_GID')

    if uid is None or gid is None:
        msg = 'this script must be run as root'
        errorExit(msg)

    # Locate applications and desktop directory
    desktopDir = os.path.join(os.path.join(os.path.expanduser('~')), 'Desktop')
    applicationsDir = os.path.normpath('/usr/share/applications')

    # Check if directories are writable
    if not os.access(desktopDir, os.W_OK | os.X_OK):
        msg = 'cannot write to Desktop folder'
        errorExit(msg)

    if not os.access(applicationsDir, os.W_OK | os.X_OK):
        msg = 'cannot write to ' + applicationsDir
        errorExit(msg)

    fDesktop = os.path.join(desktopDir, 'tapeimgr.desktop')
    fApplications = os.path.join(applicationsDir, 'tapeimgr.desktop')

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
        with io.open(fDesktop, "w", encoding="utf-8") as fD:
            for line in desktopList:
                fD.write(line + '\n')
        # Change owner to user (since script is executed as root)
        os.chown(fDesktop, int(uid), int(gid))
    except:
        msg = 'Failed to create ' + fDesktop
        errorExit(msg)

    # Write desktop file to applications directory
    try:
        infoMessage('creating launcher in applications directory ...')
        with io.open(fApplications, "w", encoding="utf-8") as fA:
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
