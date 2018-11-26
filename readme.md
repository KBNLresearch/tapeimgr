# tapeimgr

## Dependencies

Tapeimgr is currently only available on Linux (but you would probably have a hard time setting up a tape drive on Windows to begin with). It wraps around the *dd* and *mt* tools, which are expected to be installed on the system. It requires Python 3.2 or more recent, and *tkinter*. If *tkinter* is not installed already, you need to install it with operating system's package manager (there is no PyInstaller package for *tkinter*). If you're using *apt* this should work:

    sudo apt-get install python3-tk

## Installation

Install tapeimgr with the following command:

    sudo pip install tapeimgr

After this run the configuration script, which creates a desktop launcher, and adds tapeimgr to the main menu:

    sudo tapeimgr-config

Depending on your distro, you may get an "Untrusted application launcher" warning the first time you try to run the desktop launcher. You can get rid of this by clicking on the "Mark as Trusted" button.

## GUI operation

Use the menu item or dsktop launcher to start tapeimgr. Since tapeimgr starts up with root privilige, which is needed to access the tape device.

## Command-line operation

## Contributors

Written by Johan van der Knijff. 

## License

Tapeimgr is released under the  Apache License 2.0.
