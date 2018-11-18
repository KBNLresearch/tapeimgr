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
except ImportError:
    import Tkinter as tk  # Python 2.x
    import tkFileDialog
    import ScrolledText
    import tkMessageBox
from . import worker
from . import config


__version__ = '0.11.0'


class carrierEntry(tk.Frame):

    """This class defines the graphical user interface + associated functions
    for associated actions
    """

    def __init__(self, parent, *args, **kwargs):
        """Initiate class"""
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.root = parent
        config.readyToStart = False
        config.finishedBatch = False
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

    def on_create(self, event=None):
        """Create new batch in rootDir"""

        # Set up logging
        self.setupLogging(self.text_handler)

        # Update state of buttons
        self.bNew.config(state='disabled')
        self.bOpen.config(state='disabled')
        self.bFinalise.config(state='normal')
        self.submit_button.config(state='normal')
        config.readyToStart = True

    def on_submit(self, event=None):
        """Process one record and add it to the queue after user pressed submit button"""

        # Fetch entered values (strip any leading / tralue whitespace characters)
        if config.enablePPNLookup:
            catid = self.catid_entry.get().strip()
            self.catidOld = catid
        else:
            catid = ""
            title = self.title_entry.get().strip()
            self.titleOld = title
        volumeNo = self.volumeNo_entry.get().strip()
        self.volumeNoOld = volumeNo
        carrierTypeCode = self.v.get()

        # Lookup carrierType for carrierTypeCode value
        for i in self.carrierTypes:
            if i[1] == carrierTypeCode:
                carrierType = i[0]

        if config.enablePPNLookup:
            # Lookup catalog identifier
            sruSearchString = '"PPN=' + str(catid) + '"'
            response = sru.search(sruSearchString, "GGC")

            if not response:
                noGGCRecords = 0
            else:
                noGGCRecords = response.sru.nr_of_records
        else:
            noGGCRecords = 1

        if not config.readyToStart:
            msg = "You must first create a batch or open an existing batch"
            tkMessageBox.showerror("Not ready", msg)
        elif not representsInt(volumeNo):
            msg = "Volume number must be integer value"
            tkMessageBox.showerror("Type mismatch", msg)
        elif int(volumeNo) < 1:
            msg = "Volume number must be greater than or equal to 1"
            tkMessageBox.showerror("Value error", msg)
        elif noGGCRecords == 0:
            # No matching record found
            msg = ("Search for PPN=" + str(catid) + " returned " +
                   "no matching record in catalog!")
            tkMessageBox.showerror("PPN not found", msg)
        else:
            if config.enablePPNLookup:
                # Matching record found. Display title and ask for confirmation
                record = next(response.records)

                # Title can be in either title element OR in title element with maintitle attribute
                titlesMain = record.titlesMain
                titles = record.titles

                if titlesMain != []:
                    title = titlesMain[0]
                else:
                    title = titles[0]

            msg = "Found title:\n\n'" + title + "'.\n\n Is this correct?"
            if tkMessageBox.askyesno("Confirm", msg):
                # Prompt operator to insert carrier in disc robot
                msg = ("Please load disc ('" + title + "', volume " + str(volumeNo) +
                       ") into the disc loader, then press 'OK'")
                tkMessageBox.showinfo("Load disc", msg)

                # Create unique identifier for this job (UUID, based on host ID and current time)
                jobID = str(uuid.uuid1())
                # Create and populate Job file
                jobFile = os.path.join(config.jobsFolder, jobID + ".txt")

                if sys.version.startswith('3'):
                    # Py3: csv.reader expects file opened in text mode
                    fJob = open(jobFile, "w", encoding="utf-8")
                elif sys.version.startswith('2'):
                    # Py2: csv.reader expects file opened in binary mode
                    fJob = open(jobFile, "wb")

                # Create CSV writer object
                jobCSV = csv.writer(fJob, lineterminator='\n')

                # Row items to list
                rowItems = ([jobID, catid, title, volumeNo, carrierType])

                # Write row to job and close file
                jobCSV.writerow(rowItems)
                fJob.close()

                # Reset entry fields and set focus on PPN / Title field
                if config.enablePPNLookup:
                    self.catid_entry.delete(0, tk.END)
                    self.catid_entry.focus_set()
                else:
                    self.title_entry.delete(0, tk.END)
                    self.title_entry.focus_set()
                self.volumeNo_entry.delete(0, tk.END)

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
        blockSizeOld = int(self.initBlocksize.get().strip())
        blockSizeNew = max(blockSizeOld - 512, 0)
        self.initBlocksize.delete(0,tk.END)
        self.initBlocksize.insert(tk.END, str(blockSizeNew))

    def increaseBlocksize(self):
        """Increase value of initBlockSize"""
        blockSizeOld = int(self.initBlocksize.get().strip())
        blockSizeNew = blockSizeOld + 512
        self.initBlocksize.delete(0,tk.END)
        self.initBlocksize.insert(tk.END, str(blockSizeNew))

    def build_gui(self):
        """Build the GUI"""
        
        self.root.title('tapeimgr')
        self.root.option_add('*tearOff', 'FALSE')
        self.grid(column=0, row=0, sticky='w')
        self.grid_columnconfigure(0, weight=2, pad=3)
        self.grid_columnconfigure(1, weight=4, pad=3)
        self.grid_columnconfigure(2, weight=0, pad=3)
        self.grid_columnconfigure(3, weight=0, pad=3)

        tk.Label(self, text='Settings', font=('', 16)).grid(column=0, row=0, sticky='w')

        # Entry elements

        # Output Directory
        tk.Label(self, text='Output Directory').grid(column=0, row=3, sticky='w')
        self.outDirButton = tk.Button(self, text='Select', command=self.selectOutputDirectory, width=15)
        self.outDirButton.grid(column=1, row=3, sticky='w')
        self.outDirLabel = tk.Label(self, text=self.outDir)
        self.outDirLabel.update()
        self.outDirLabel.grid(column=1, row=4, sticky='w')
        
        # Tape Device
        tk.Label(self, text='Tape Device').grid(column=0, row=5, sticky='w')
        self.tapeDevice = tk.Entry(self, width=20)
        self.tapeDevice['background'] = 'white'
        self.tapeDevice.insert(tk.END,'/dev/nst0')
        self.tapeDevice.grid(column=1, row=5, sticky='w')

        # Initial Block Size
        tk.Label(self, text='Initial Block Size').grid(column=0, row=6, sticky='w')
        self.initBlocksize = tk.Entry(self, width=20)
        self.initBlocksize['background'] = 'white'
        self.initBlocksize.insert(tk.END,'512')
        self.initBlocksize.grid(column=1, row=6, sticky='w')
        self.decreaseBSButton = tk.Button(self, text='-', command=self.decreaseBlocksize, width=1)
        self.decreaseBSButton.grid(column=2, row=6, sticky='w')
        self.increaseBSButton = tk.Button(self, text='+', command=self.increaseBlocksize, width=1)
        self.increaseBSButton.grid(column=3, row=6, sticky='w')

        # Sessions
        tk.Label(self, text='Sessions').grid(column=0, row=7, sticky='w')
        self.sessions = tk.Entry(self, width=20)
        self.sessions['background'] = 'white'
        self.sessions.grid(column=1, row=7, sticky='w')

        # Prefix
        tk.Label(self, text='Prefix').grid(column=0, row=8, sticky='w')
        self.prefix = tk.Entry(self, width=20)
        self.prefix['background'] = 'white'
        self.prefix.insert(tk.END,'session')
        self.prefix.grid(column=1, row=8, sticky='w')

        # Extension
        tk.Label(self, text='Extension').grid(column=0, row=9, sticky='w')
        self.extension = tk.Entry(self, width=20)
        self.extension['background'] = 'white'
        self.extension.insert(tk.END,'dd')
        self.extension.grid(column=1, row=9, sticky='w')

        # Fill failed blocks
        tk.Label(self, text='Fill failed blocks').grid(column=0, row=10, sticky='w')
        fillBlocks = tk.IntVar()
        self.fillblocks = tk.Checkbutton(self, variable=fillBlocks)
        self.fillblocks.grid(column=1, row=10, sticky='w')

        self.start_button = tk.Button(self,
                                       text='Start',
                                       width=15,
                                       underline=0,
                                       command=self.on_submit)
        self.start_button.grid(column=1, row=13, sticky='w')

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
        self.root.bind_all('<Control-Key-n>', self.on_create)
        self.root.bind_all('<Control-Key-o>', self.on_create)
        self.root.bind_all('<Control-Key-f>', self.on_create)
        self.root.bind_all('<Control-Key-e>', self.on_quit)
        self.root.bind_all('<Control-Key-s>', self.on_create)

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
        carrierEntry(root)

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
