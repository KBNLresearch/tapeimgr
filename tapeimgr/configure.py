#! /usr/bin/env python3

"""Post-install / configuration script for tapeimgr"""

import os
import io
import sys


def errorExit(msg):
    """Print error to stderr and exit"""
    msgString = ('ERROR: ' + msg + '\n')
    sys.stderr.write(msgString)
    sys.exit(1)


def post_install():
    """
    Creates .desktop files in user directory and on desktop
    """

    uid = os.environ.get('SUDO_UID')
    gid = os.environ.get('SUDO_GID')

    if uid == None or gid == None:
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

    # Locate icon file in package dir
    packageDir = os.path.dirname(os.path.abspath(__file__))
    iconFile = os.path.join(packageDir, 'icons', 'tapeimgr.png')
    if not os.path.isfile(iconFile):
        msg = 'cannot find icon file'
        errorExit(msg)

    # List of desktop file lines
    desktopList = []
    desktopList.append('[Desktop Entry]')
    desktopList.append('Type=Application')
    desktopList.append('Encoding=UTF-8')
    desktopList.append('Name=tapeimgr')
    desktopList.append('Comment=Simple tape imaging and extraction tool')
    desktopList.append('Exec=gksudo -k tapeimgr')
    desktopList.append('Icon=' + iconFile)
    desktopList.append('Terminal=false')
    desktopList.append('Categories=Utility;System;GTK')

    # Write file to Desktop
    try:
        with io.open(fDesktop, "w", encoding="utf-8") as fD:
            for line in desktopList:
                fD.write(line + '\n')
        # Change owner to user (since script is executed as root)
        os.chown(fDesktop, int(uid), int(gid))
    except:
        msg = 'Failed to create ' + fDesktop
        errorExit(msg)
    
    # Write file to applications directory
    try:
        with io.open(fApplications, "w", encoding="utf-8") as fA:
            for line in desktopList:
                fA.write(line + '\n')
    except:
        msg = 'Failed to create desktop ' + fApplications
        errorExit(msg)

    msg = 'tapeimgr configuration completed successfully!\n'
    sys.stdout.write(msg)


def main():
    """Main function"""
    post_install()


if __name__ == "__main__":
    main()
