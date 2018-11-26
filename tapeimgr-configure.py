#! /usr/bin/env python3

"""Wrapper script, ensures that relative imports work correctly in a PyInstaller build"""

from tapeimgr.configure import main

if __name__ == '__main__':
    main()
