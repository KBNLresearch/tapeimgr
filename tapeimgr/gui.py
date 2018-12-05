#! /usr/bin/env python3
"""
Tapeimgr, automated reading of tape
Graphical user interface

Author: Johan van der Knijff
Research department,  KB / National Library of the Netherlands
"""

import sys
import os
import time
import threading
import logging
import queue
import tkinter as tk
from tkinter import filedialog as tkFileDialog
from tkinter import scrolledtext as ScrolledText
from tkinter import messagebox as tkMessageBox
from tkinter import ttk
from .tape import Tape
from . import config


class tapeimgrGUI(tk.Frame):

    """This class defines the graphical user interface + associated functions
    for associated actions
    """

    def __init__(self, parent, *args, **kwargs):
        """Initiate class"""
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.root = parent
        # Logging stuff
        self.logger = logging.getLogger()
        # Create a logging handler using a queue
        self.log_queue = queue.Queue(-1)
        self.queue_handler = QueueHandler(self.log_queue)
        # Create tape instance
        self.tape = Tape()
        self.t1 = None
        # Read configuration file
        self.tape.getConfiguration()
        # Build the GUI
        self.build_gui()

    def on_quit(self):
        """Quit tapeimgr"""
        os._exit(0)

    def on_submit(self):
        """fetch and validate entered input, and start processing"""

        # This flag is true if all input validates
        inputValidateFlag = True

        # Fetch entered values (strip any leading / trailing whitespace characters)
        self.tape.tapeDevice = self.tapeDevice_entry.get().strip()
        self.tape.initBlockSize = self.initBlockSize_entry.get().strip()
        self.tape.files = self.files_entry.get().strip()
        self.tape.prefix = self.prefix_entry.get().strip()
        self.tape.extension = self.extension_entry.get().strip()
        self.tape.fillBlocks = self.fBlocks.get()

        # Validate input
        self.tape.validateInput()

        # Show error message for any parameters that didn't pass validation
        if not self.tape.dirOutIsDirectory:
            inputValidateFlag = False
            msg = ("Output directory doesn't exist:\n" + self.tape.dirOut)
            tkMessageBox.showerror("ERROR", msg)

        if not self.tape.dirOutIsWritable:
            inputValidateFlag = False
            msg = ('Cannot write to directory ' + self.tape.dirOut)
            tkMessageBox.showerror("ERROR", msg)

        if not self.tape.deviceAccessibleFlag:
            inputValidateFlag = False
            msg = ('Tape device is not accessible')
            tkMessageBox.showerror("ERROR", msg)

        if not self.tape.blockSizeIsValid:
            inputValidateFlag = False
            msg = ('Block size not valid')
            tkMessageBox.showerror("ERROR", msg)

        if not self.tape.filesIsValid:
            inputValidateFlag = False
            msg = ('Files value not valid\n'
                   '(must be comma-delimited string of integer numbers, or empty)')
            tkMessageBox.showerror("ERROR", msg)

        # Ask confirmation if output files exist already
        outDirConfirmFlag = True
        if self.tape.outputExistsFlag:
            msg = ('writing to ' + self.tape.dirOut + ' will overwrite existing files!\n'
                   'press OK to continue, otherwise press Cancel ')
            outDirConfirmFlag = tkMessageBox.askokcancel("Overwrite files?", msg)

        if inputValidateFlag and outDirConfirmFlag:

            # Start logger
            successLogger = True
            try:
                self.setupLogger()
                # Start polling log messages from the queue
                self.after(100, self.poll_log_queue)
            except OSError:
                # Something went wrong while trying to write to lof file
                msg = ('error trying to write log file to ' + self.tape.logFile)
                tkMessageBox.showerror("ERROR", msg)
                successLogger = False

            if successLogger:
                # Disable start and exit buttons
                self.start_button.config(state='disabled')
                self.quit_button.config(state='disabled')

                # Launch tape processing function as subprocess
                self.t1 = threading.Thread(target=self.tape.processTape)
                self.t1.start()


    def selectOutputDirectory(self, event=None):
        """Select output directory"""
        dirInit = self.tape.dirOut
        self.tape.dirOut = tkFileDialog.askdirectory(initialdir=dirInit)
        self.outDirLabel['text'] = self.tape.dirOut

    def decreaseBlocksize(self):
        """Decrease value of initBlockSize"""
        try:
            blockSizeOld = int(self.initBlockSize_entry.get().strip())
        except ValueError:
            # Reset if user manually entered something weird
            blockSizeOld = int(self.tape.initBlockSizeDefault)
        blockSizeNew = max(blockSizeOld - 512, 512)
        self.initBlockSize_entry.delete(0, tk.END)
        self.initBlockSize_entry.insert(tk.END, str(blockSizeNew))

    def increaseBlocksize(self):
        """Increase value of initBlockSize"""
        try:
            blockSizeOld = int(self.initBlockSize_entry.get().strip())
        except ValueError:
            # Reset if user manually entered something weird
            blockSizeOld = int(self.tape.initBlockSizeDefault)
        blockSizeNew = blockSizeOld + 512
        self.initBlockSize_entry.delete(0, tk.END)
        self.initBlockSize_entry.insert(tk.END, str(blockSizeNew))

    def build_gui(self):
        """Build the GUI"""

        self.root.title('tapeimgr v.' + config.version)
        self.root.option_add('*tearOff', 'FALSE')
        self.grid(column=0, row=0, sticky='w')
        self.grid_columnconfigure(0, weight=0, pad=0)
        self.grid_columnconfigure(1, weight=0, pad=0)
        self.grid_columnconfigure(2, weight=0, pad=0)
        self.grid_columnconfigure(3, weight=0, pad=0)

        # Entry elements
        ttk.Separator(self, orient='horizontal').grid(column=0, row=0, columnspan=4, sticky='ew')
        # Output Directory
        self.outDirButton_entry = tk.Button(self,
                                            text='Select Output Directory',
                                            command=self.selectOutputDirectory,
                                            width=20)
        self.outDirButton_entry.grid(column=0, row=3, sticky='w')
        self.outDirLabel = tk.Label(self, text=self.tape.dirOut)
        self.outDirLabel.update()
        self.outDirLabel.grid(column=1, row=3, sticky='w')

        ttk.Separator(self, orient='horizontal').grid(column=0, row=5, columnspan=4, sticky='ew')

        # Tape Device
        tk.Label(self, text='Tape Device').grid(column=0, row=6, sticky='w')
        self.tapeDevice_entry = tk.Entry(self, width=20)
        self.tapeDevice_entry['background'] = 'white'
        self.tapeDevice_entry.insert(tk.END, self.tape.tapeDevice)
        self.tapeDevice_entry.grid(column=1, row=6, sticky='w')

        # Initial Block Size
        tk.Label(self, text='Initial Block Size').grid(column=0, row=7, sticky='w')
        self.initBlockSize_entry = tk.Entry(self, width=20)
        self.initBlockSize_entry['background'] = 'white'
        self.initBlockSize_entry.insert(tk.END, self.tape.initBlockSize)
        self.initBlockSize_entry.grid(column=1, row=7, sticky='w')
        self.decreaseBSButton = tk.Button(self, text='-', command=self.decreaseBlocksize, width=1)
        self.decreaseBSButton.grid(column=2, row=7, sticky='e')
        self.increaseBSButton = tk.Button(self, text='+', command=self.increaseBlocksize, width=1)
        self.increaseBSButton.grid(column=3, row=7, sticky='w')

        # Files
        tk.Label(self, text='Files (comma-separated list)').grid(column=0, row=8, sticky='w')
        self.files_entry = tk.Entry(self, width=20)
        self.files_entry['background'] = 'white'
        self.files_entry.insert(tk.END, self.tape.files)
        self.files_entry.grid(column=1, row=8, sticky='w')

        # Prefix
        tk.Label(self, text='Prefix').grid(column=0, row=9, sticky='w')
        self.prefix_entry = tk.Entry(self, width=20)
        self.prefix_entry['background'] = 'white'
        self.prefix_entry.insert(tk.END, self.tape.prefix)
        self.prefix_entry.grid(column=1, row=9, sticky='w')

        # Extension
        tk.Label(self, text='Extension').grid(column=0, row=10, sticky='w')
        self.extension_entry = tk.Entry(self, width=20)
        self.extension_entry['background'] = 'white'
        self.extension_entry.insert(tk.END, self.tape.extension)
        self.extension_entry.grid(column=1, row=10, sticky='w')

        # Fill failed blocks
        tk.Label(self, text='Fill failed blocks').grid(column=0, row=11, sticky='w')
        self.fBlocks = tk.IntVar()
        self.fillblocks_entry = tk.Checkbutton(self, variable=self.tape.fillBlocks)
        self.fillblocks_entry.grid(column=1, row=11, sticky='w')

        ttk.Separator(self, orient='horizontal').grid(column=0, row=12, columnspan=4, sticky='ew')

        self.start_button = tk.Button(self,
                                      text='Start',
                                      width=10,
                                      underline=0,
                                      command=self.on_submit)
        self.start_button.grid(column=1, row=13, sticky='e')

        self.quit_button = tk.Button(self,
                                     text='Exit',
                                     width=10,
                                     underline=0,
                                     command=self.on_quit)
        self.quit_button.grid(column=2, row=13, sticky='w', columnspan=2)

        ttk.Separator(self, orient='horizontal').grid(column=0, row=14, columnspan=4, sticky='ew')

        # Add ScrolledText widget to display logging info
        self.st = ScrolledText.ScrolledText(self, state='disabled', height=15)
        self.st.configure(font='TkFixedFont')
        self.st['background'] = 'white'
        self.st.grid(column=0, row=15, sticky='ew', columnspan=4)

        # Define bindings for keyboard shortcuts: buttons
        self.root.bind_all('<Control-Key-d>', self.selectOutputDirectory)
        self.root.bind_all('<Control-Key-s>', self.on_submit)
        self.root.bind_all('<Control-Key-e>', self.on_quit)

        for child in self.winfo_children():
            child.grid_configure(padx=5, pady=5)

        # Display message and exit if config file could not be read
        if not self.tape.configSuccess:
            msg = ("Error reading configuration file! \n" +
                   "Run '(sudo) tapeimgr-config' to fix this.")
            errorExit(msg)

    def reset_gui(self):
        """Reset the GUI"""
        # Create new tape instance
        self.tape = Tape()
        # Read configuration
        self.tape.getConfiguration()
        # Logging stuff
        self.logger = logging.getLogger()
        # Create a logging handler using a queue
        self.log_queue = queue.Queue(-1)
        self.queue_handler = QueueHandler(self.log_queue)
        # Reset all entry widgets
        self.outDirLabel['text'] = self.tape.dirOut
        self.tapeDevice_entry.delete(0, tk.END)
        self.tapeDevice_entry.insert(tk.END, self.tape.tapeDevice)
        self.initBlockSize_entry.delete(0, tk.END)
        self.initBlockSize_entry.insert(tk.END, self.tape.initBlockSize)
        self.files_entry.delete(0, tk.END)
        self.files_entry.insert(tk.END, self.tape.files)
        self.prefix_entry.delete(0, tk.END)
        self.prefix_entry.insert(tk.END, self.tape.prefix)
        self.extension_entry.delete(0, tk.END)
        self.extension_entry.insert(tk.END, self.tape.extension)
        self.fillblocks_entry.variable = self.tape.fillBlocks
        self.start_button.config(state='normal')
        self.quit_button.config(state='normal')

    def setupLogger(self):
        """Set up logger configuration"""

        # Basic configuration
        logging.basicConfig(filename=self.tape.logFile,
                            level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')

        # Add the handler to logger
        self.logger = logging.getLogger()

        # This sets the console output format (slightly different from basicConfig!)
        formatter = logging.Formatter('%(levelname)s: %(message)s')
        self.queue_handler.setFormatter(formatter)
        self.logger.addHandler(self.queue_handler)

    def display(self, record):
        """Display log record in scrolledText widget"""
        msg = self.queue_handler.format(record)
        self.st.configure(state='normal')
        self.st.insert(tk.END, msg + '\n', record.levelname)
        self.st.configure(state='disabled')
        # Autoscroll to the bottom
        self.st.yview(tk.END)

    def poll_log_queue(self):
        """Check every 100ms if there is a new message in the queue to display"""
        while True:
            try:
                record = self.log_queue.get(block=False)
            except queue.Empty:
                break
            else:
                self.display(record)
        self.after(100, self.poll_log_queue)


class QueueHandler(logging.Handler):
    """Class to send logging records to a queue

    It can be used from different threads
    The ConsoleUi class polls this queue to display records in a ScrolledText widget
    Taken from https://github.com/beenje/tkinter-logging-text-widget/blob/master/main.py
    """

    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(record)


def checkDirExists(dirIn):
    """Check if directory exists and exit if not"""
    if not os.path.isdir(dirIn):
        msg = ('directory ' + dirIn + ' does not exist!')
        tkMessageBox.showerror("Error", msg)
        sys.exit(1)


def errorExit(error):
    """Show error message in messagebox and then exit after user presses OK"""
    tkMessageBox.showerror("Error", error)
    os._exit(1)


def main():
    """Main function"""

    packageDir = os.path.dirname(os.path.abspath(__file__))
    root = tk.Tk()
    root.iconphoto(True, tk.PhotoImage(file=os.path.join(packageDir, 'icons', 'tapeimgr.png')))
    myGUI = tapeimgrGUI(root)
    # This ensures application quits normally if user closes window
    root.protocol('WM_DELETE_WINDOW', myGUI.on_quit)

    while True:
        try:
            root.update_idletasks()
            root.update()
            time.sleep(0.1)
            if myGUI.tape.finishedFlag:
                myGUI.t1.join()
                #myGUI.logger.removeHandler(myGUI.queue_handler)
                #myGUI.queue_handler.close()
                handlers = myGUI.logger.handlers[:]
                for handler in handlers:
                    handler.close()
                    myGUI.logger.removeHandler(handler)

                if myGUI.tape.tapeDeviceIOError:
                    # Tape device not accessible
                    msg = ('Cannot access tape device ' + myGUI.tape.tapeDevice +
                           '. Check that device exits, and that tapeimgr is run as root')
                    errorExit(msg)
                elif myGUI.tape.successFlag:
                    # Tape extraction completed with no errors
                    msg = ('Tape processed successfully without errors')
                    tkMessageBox.showinfo("Success", msg)
                else:
                    # Tape extraction resulted in errors
                    msg = ('One or more errors occurred while processing tape, '
                           'check log file for details')
                    tkMessageBox.showwarning("Errors occurred", msg)

                # Reset the GUI
                myGUI.reset_gui()

        except Exception as e:
            # Unexpected error
            msg = 'An unexpected error occurred, see log file for details'
            logging.error(e, exc_info=True)
            errorExit(msg)

if __name__ == "__main__":
    main()
