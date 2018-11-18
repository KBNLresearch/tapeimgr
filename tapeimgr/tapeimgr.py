#! /usr/bin/env python
"""
Script for automated reading of tape

Author: Johan van der Knijff
Research department,  KB / National Library of the Netherlands

"""

import sys
import os
import imp
import time
import threading
import logging
try:
    import tkinter as tk  # Python 3.x
    from tkinter import filedialog as tkFileDialog
    from tkinter import scrolledtext as ScrolledText
    from tkinter import messagebox as tkMessageBox
    from tkinter import ttk
except ImportError:
    import Tkinter as tk  # Python 2.x
    import tkFileDialog
    import ScrolledText
    import tkMessageBox
    import ttk
from . import shared
from . import worker
from . import config


__version__ = '0.11.0'


class tapeimgrGUI(tk.Frame):

    """This class defines the graphical user interface + associated functions
    for associated actions
    """

    def __init__(self, parent, *args, **kwargs):
        """Initiate class"""
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.root = parent
        config.readyToStart = False
        config.finishedTape = False
        self.catidOld = ""
        self.titleOld = ""
        self.volumeNoOld = ""
        self.outDir = "/"
        self.build_gui()

    def on_quit(self, event=None):
        """Wait until the disc that is currently being pocessed has
        finished, and quit (batch can be resumed by opening it in the File dialog)
        """
        config.quitFlag = True
        self.bExit.config(state='disabled')
        self.bFinalise.config(state='disabled')
        msg = 'User pressed Exit, quitting after current disc has been processed'
        tkMessageBox.showinfo("Info", msg)
        if not config.readyToStart:
            # Wait 2 seconds to avoid race condition
            time.sleep(2)
            msg = 'Quitting because user pressed Exit, click OK to exit'
            tkMessageBox.showinfo("Exit", msg)
            os._exit(0)

    def on_submit(self, event=None):
        """fetch and validate entered input"""

        # Fetch entered values (strip any leading / traling whitespace characters)
        config.tapeDevice = self.tapeDevice_entry.get().strip()
        config.initBlocksize = self.initBlocksize_entry.get().strip()
        config.prefix = self.prefix_entry.get().strip()
        config.extension = self.extension_entry.get().strip()
        config.fillBlocks = self.fBlocks.get()

        print(config.tapeDevice, config.initBlocksize, config.prefix, config.extension, config.fillBlocks)

        # Check if block size is valid (i.e. a multiple of 512)
        blocksizeValid = False
        try:
            noBlocks = (int(config.initBlocksize)/512)

            if not noBlocks.is_integer():
                msg = "Initial block size must be a multiple of 512"
                tkMessageBox.showerror("ERROR", msg)
            elif noBlocks == 0:
                msg = "Initial block size cannot be 0"
                tkMessageBox.showerror("ERROR", msg)
            else:
                blocksizeValid = True

        except ValueError:
            msg = "Initial block size must be a number"
            tkMessageBox.showerror("ERROR", msg)
        
        if blocksizeValid:
            # This flag tells worker module tape extraction can start 
            config.readyToStart = True
        
        print(config.readyToStart)

    def setupLogging(self, handler):
        """Set up logging-related settings"""
        logFile = os.path.join('.', 'batch.log')

        logging.basicConfig(handlers=[logging.FileHandler(logFile, 'a', 'utf-8')],
                            level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')

        # Add the handler to logger
        logger = logging.getLogger()
        logger.addHandler(handler)

    def selectOutputDirectory(self):
        """Select output directory"""
        self.outDir = tkFileDialog.askdirectory(initialdir="/")
        print(self.outDir)
        self.outDirLabel['text'] = self.outDir

    def decreaseBlocksize(self):
        """Decrease value of initBlockSize"""
        blockSizeOld = int(self.initBlocksize_entry.get().strip())
        blockSizeNew = max(blockSizeOld - 512, 512)
        self.initBlocksize_entry.delete(0,tk.END)
        self.initBlocksize_entry.insert(tk.END, str(blockSizeNew))

    def increaseBlocksize(self):
        """Increase value of initBlockSize"""
        blockSizeOld = int(self.initBlocksize_entry.get().strip())
        blockSizeNew = blockSizeOld + 512
        self.initBlocksize_entry.delete(0,tk.END)
        self.initBlocksize_entry.insert(tk.END, str(blockSizeNew))

    def build_gui(self):
        """Build the GUI"""
        
        self.root.title('tapeimgr')
        self.root.option_add('*tearOff', 'FALSE')
        self.grid(column=0, row=0, sticky='w')
        self.grid_columnconfigure(0, weight=2, pad=3)
        self.grid_columnconfigure(1, weight=4, pad=3)
        self.grid_columnconfigure(2, weight=0, pad=3)
        self.grid_columnconfigure(3, weight=0, pad=3)

        # Entry elements
        ttk.Separator(self, orient='horizontal').grid(column=0, row=0, columnspan=4, sticky='ew')
        # Output Directory
        #tk.Label(self, text='Output Directory').grid(column=0, row=3, sticky='w')
        self.outDirButton_entry = tk.Button(self, text='Select Output Directory', command=self.selectOutputDirectory, width=20)
        self.outDirButton_entry.grid(column=0, row=3, sticky='w')
        self.outDirLabel = tk.Label(self, text=self.outDir)
        self.outDirLabel.update()
        self.outDirLabel.grid(column=1, row=3, sticky='w')

        ttk.Separator(self, orient='horizontal').grid(column=0, row=5, columnspan=4, sticky='ew')

        # Tape Device
        tk.Label(self, text='Tape Device').grid(column=0, row=6, sticky='w')
        self.tapeDevice_entry = tk.Entry(self, width=20)
        self.tapeDevice_entry['background'] = 'white'
        self.tapeDevice_entry.insert(tk.END, config.tapeDevice)
        self.tapeDevice_entry.grid(column=1, row=6, sticky='w')

        # Initial Block Size
        tk.Label(self, text='Initial Block Size').grid(column=0, row=7, sticky='w')
        self.initBlocksize_entry = tk.Entry(self, width=20)
        self.initBlocksize_entry['background'] = 'white'
        self.initBlocksize_entry.insert(tk.END, config.initBlocksize)
        self.initBlocksize_entry.grid(column=1, row=7, sticky='w')
        self.decreaseBSButton = tk.Button(self, text='-', command=self.decreaseBlocksize, width=1)
        self.decreaseBSButton.grid(column=2, row=7, sticky='w')
        self.increaseBSButton = tk.Button(self, text='+', command=self.increaseBlocksize, width=1)
        self.increaseBSButton.grid(column=3, row=7, sticky='w')

        # Sessions
        tk.Label(self, text='Sessions (comma-separated list)').grid(column=0, row=8, sticky='w')
        self.sessions_entry = tk.Entry(self, width=20)
        self.sessions_entry['background'] = 'white'
        self.sessions_entry.grid(column=1, row=8, sticky='w')

        # Prefix
        tk.Label(self, text='Prefix').grid(column=0, row=9, sticky='w')
        self.prefix_entry = tk.Entry(self, width=20)
        self.prefix_entry['background'] = 'white'
        self.prefix_entry.insert(tk.END, config.prefix)
        self.prefix_entry.grid(column=1, row=9, sticky='w')

        # Extension
        tk.Label(self, text='Extension').grid(column=0, row=10, sticky='w')
        self.extension_entry = tk.Entry(self, width=20)
        self.extension_entry['background'] = 'white'
        self.extension_entry.insert(tk.END, config.extension)
        self.extension_entry.grid(column=1, row=10, sticky='w')

        # Fill failed blocks
        tk.Label(self, text='Fill failed blocks').grid(column=0, row=11, sticky='w')
        self.fBlocks = tk.IntVar()
        self.fillblocks_entry = tk.Checkbutton(self, variable=self.fBlocks)
        self.fillblocks_entry.grid(column=1, row=11, sticky='w')

        ttk.Separator(self, orient='horizontal').grid(column=0, row=12, columnspan=4, sticky='ew')

        self.start_button = tk.Button(self,
                                       text='Start',
                                       width=15,
                                       underline=0,
                                       command=self.on_submit)
        self.start_button.grid(column=1, row=13, sticky='w')

        ttk.Separator(self, orient='horizontal').grid(column=0, row=14, columnspan=4, sticky='ew')

        # Add ScrolledText widget to display logging info
        st = ScrolledText.ScrolledText(self, state='disabled', height=15)
        st.configure(font='TkFixedFont')
        st['background'] = 'white'
        st.grid(column=0, row=15, sticky='ew', columnspan=4)

        # Create textLogger
        self.text_handler = TextHandler(st)

       # Logging configuration
        logging.basicConfig(filename='test.log',
            level=logging.INFO, 
            format='%(asctime)s - %(levelname)s - %(message)s')        

        # Add the handler to logger
        logger = logging.getLogger()        
        logger.addHandler(self.text_handler)

        # Define bindings for keyboard shortcuts: buttons
        self.root.bind_all('<Control-Key-s>', self.on_submit)
        self.root.bind_all('<Control-Key-e>', self.on_quit)

        # TODO keyboard shortcuts for Radiobox selections: couldn't find ANY info on how to do this!

        for child in self.winfo_children():
            child.grid_configure(padx=5, pady=5)

class TextHandler(logging.Handler):
    """This class allows you to log to a Tkinter Text or ScrolledText widget
    Adapted from: https://gist.github.com/moshekaplan/c425f861de7bbf28ef06
    """

    def __init__(self, text):
        """Run the regular Handler __init__"""
        logging.Handler.__init__(self)
        # Store a reference to the Text it will log to
        self.text = text

    def emit(self, record):
        """Add a record to the widget"""
        msg = self.format(record)

        def append():
            """Append text"""
            self.text.configure(state='normal')
            self.text.insert(tk.END, msg + '\n')
            self.text.configure(state='disabled')
            # Autoscroll to the bottom
            self.text.yview(tk.END)
        # This is necessary because we can't modify the Text from other threads
        self.text.after(0, append)


def checkDirExists(dirIn):
    """Check if directory exists and exit if not"""
    if not os.path.isdir(dirIn):
        msg = "directory " + dirIn + " does not exist!"
        tkMessageBox.showerror("Error", msg)
        sys.exit()


def errorExit(error):
    """Show error message in messagebox and then exit after userv presses OK"""
    tkMessageBox.showerror("Error", error)
    sys.exit()


def main_is_frozen():
    """Return True if application is frozen (Py2Exe), and False otherwise"""
    return (hasattr(sys, "frozen") or  # new py2exe
            hasattr(sys, "importers") or  # old py2exe
            imp.is_frozen("__main__"))  # tools/freeze


def get_main_dir():
    """Return application (installation) directory"""
    if main_is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(sys.argv[0])

def main():
    """Main function"""

    try:
        root = tk.Tk()
        tapeimgrGUI(root)

        t1 = threading.Thread(target=worker.worker, args=[])
        t1.start()

        root.mainloop()
        t1.join()
    except KeyboardInterrupt:
        if config.finishedBatch:
            # Batch finished: notify user
            msg = 'Completed processing this batch, click OK to exit'
            tkMessageBox.showinfo("Finished", msg)
        elif config.quitFlag:
            # User pressed exit; notify user
            msg = 'Quitting because user pressed Exit, click OK to exit'
            tkMessageBox.showinfo("Exit", msg)
        os._exit(0)

if __name__ == "__main__":
    main()
