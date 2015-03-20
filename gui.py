#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Create Date    :  2015-03-14 13:31
# Python Version :  %PYVER%
# Git Repo       :  https://github.com/Jerry-Ma
# Email Address  :  jerry.ma.nk@gmail.com
"""
gui.py
"""

'''
The tk gui class
'''


import Tkinter
import ttk
import tkFileDialog
import tkFont
import webbrowser
import os
import subprocess

import adpdeb
import utils


class AdaptiveDeblendingUI(ttk.Frame):

    def __init__(self):

        s = ttk.Style()
        s.theme_use('default')
        ttk.Frame.__init__(self, None)
        self.master.title("Adaptive De-blending Tool")
        self.master.minsize(320, 240)
        swd = self.master.winfo_screenwidth()
        fwd = 480
        fht = 360
        self.master.geometry('+{0:d}+{1:d}'.format(swd - fwd - 10, 0))
        self.master.minsize(fwd, fht)

        self.central = ttk.Frame(self.master)
        self.central.pack(side=Tkinter.TOP, fill=Tkinter.BOTH, expand=1)
        self.workzone = ttk.Frame(self.central)
        self.workzone.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH, expand=1)
        self.notebook = ttk.Notebook(self.workzone,
                                     name='messageNotebook', height=1, width=1)
        self.notebook.pack(fill=Tkinter.BOTH, expand=1)
        self.tab = []  # 1 coord tab 2 par tab 3 run tab
        self.box = []
        for i in ['coord', 'parfile', 'output']:
            self._add_tab(i)

        self.inputzone = ttk.Frame(self.central, width=160)
        self.inputzone.pack(side=Tkinter.RIGHT, fill=Tkinter.BOTH, expand=0)
        self.inputzonetop = ttk.Frame(self.inputzone)
        self.inputzonetop.pack(side=Tkinter.TOP, fill=Tkinter.X, expand=0)
        self.inputzonebottom = ttk.Frame(self.inputzone)
        self.inputzonebottom.pack(side=Tkinter.BOTTOM,
                                  fill=Tkinter.BOTH, expand=1)

        self.loadinputbutton = ttk.Button(self.inputzonetop,
                                          text="Open...",
                                          command=self.load_input_file,
                                          width=5)
        self.loadinputbutton.pack(side=Tkinter.LEFT,
                                  fill=Tkinter.X, expand=0,
                                  padx=3, pady=0)
        self.selectinputcombobox = ttk.Combobox(self.inputzonetop,
                                                width=10,
                                                state=Tkinter.DISABLED)
        self.selectinputcombobox.pack(side=Tkinter.RIGHT,
                                      fill=Tkinter.BOTH, expand=1)

        self.displayinfo = Tkinter.StringVar()
        f = tkFont.Font(family="Courier")
        self.displayinfolabel = ttk.Label(self.inputzonebottom,
                                          textvariable=self.displayinfo,
                                          font=f,
                                          wraplength=160,
                                          anchor=Tkinter.NW)
        self.displayinfolabel.pack(side=Tkinter.TOP,
                                      fill=Tkinter.BOTH, expand=1)
        self.logfileinfo = Tkinter.StringVar()
        self.logfileinfolabel = ttk.Label(self.inputzonebottom,
                                    textvariable=self.logfileinfo,
                                          cursor='hand2',
                                          foreground="#0000ff")
        self.logfileinfolabel.pack(side=Tkinter.BOTTOM,
                                  fill=Tkinter.BOTH, expand=0)

        self.status = Tkinter.StringVar()
        self.statusbar = ttk.Frame(self.master, height=25)
        self.statusbar.pack(side=Tkinter.BOTTOM,
                            fill=Tkinter.BOTH, expand=0)
        self.statusbar.pack_propagate(0)
        self.statuslabel = ttk.Label(self.statusbar,
                                   textvariable=self.status,
                                   anchor=Tkinter.W,
                                   )
        self.statuslabel.pack(side=Tkinter.LEFT,
                              fill=Tkinter.BOTH, expand=1)
        self.runbutton = ttk.Button(self.statusbar, text="GalFit",
                                    state=Tkinter.DISABLED,
                                    command=self.run_galfit)
        self.runbutton.pack(side=Tkinter.RIGHT,
                            fill=Tkinter.BOTH, expand=0)
        self.pack()
        self.bind_all("<Return>", lambda e: self.runbutton.invoke())
        self.runbutton.focus()
        self.selectinputcombobox.bind('<<ComboboxSelected>>',
                                      lambda e: self.display_input(
                                       self.selectinputcombobox.current()))
        self.logfileinfolabel.bind('<Button-1>', lambda e: self.open_logfile())
        self.notebook.bind('<<NotebookTabChanged>>', lambda e: self.reset_selection())
        self.sourceselector = None
        self.fnull = open(os.devnull, "w")
        self.process_xclipboard()

    def process_xclipboard(self):
        if self.sourceselector is None:
            self.status.set('Please load the input file ...')
        else:
            if self.notebook.index(self.notebook.select()) == 0:
                self.status.set('Use DS9 to select objects ...')
                self.box[0].delete('1.0', Tkinter.END)
                try:
                    xclip = subprocess.check_output([
                            self.sourceselector.xclip_bin, '-o'],
                            stderr=self.fnull)
                except subprocess.CalledProcessError:
                    xclip = ""
                self.sourceselector.selected = utils.parse_ds9xclipboard(xclip)
                if len(self.sourceselector.selected) > 0:
                    self.box[0].insert(Tkinter.END,
                                   self.sourceselector.pretty_print_selected())
                    self.runbutton.config(state=Tkinter.ACTIVE)
                else:
                    self.box[0].insert(Tkinter.END,
                                   "No object is selected")
                    self.runbutton.config(state=Tkinter.DISABLED)
        self.master.after(500, self.process_xclipboard)

    def run_galfit(self, event=None):
        self.runbutton.config(state=Tkinter.DISABLED)
        self.notebook.select(1)
        self.status.set('Compose GalFit parameter file ...')
        self.update_idletasks()
        self.box[1].delete('1.0', Tkinter.END)
        self.box[1].insert(Tkinter.END,
                        self.sourceselector.gen_galfit_parfile())
        self.notebook.select(2)
        self.status.set('Run GalFit ...')
        self.update_idletasks()
        self.box[2].delete('1.0', Tkinter.END)
        self.box[2].insert(Tkinter.END,
                        self.sourceselector.run_galfit())
        if self.sourceselector.galfit_result == "":
            self.status.set('GalFit fails!')
            self.update_idletasks()
        else:
            self.status.set('Success!')
            self.update_idletasks()
            self.sourceselector.load_result()
        self.sourceselector.write_to_log()

    def reset_selection(self):
        if self.sourceselector is not None:
            if self.notebook.index(self.notebook.select()) == 0:
                self.sourceselector.show_low_res_coord()

    def load_input_file(self):

        inputfile = tkFileDialog.askopenfilename(
            parent=self.master,
            filetypes=[("Input file", "*.input"), ("All files", "*.*")],
            title="Choose input file to load"
            )
        if inputfile:
            self.selectinputcombobox.config(state=Tkinter.NORMAL)
            try:
                self.sourceselector = adpdeb.SourceSelector(
                    **utils.parse_inputfile(inputfile))
            except AssertionError as e:
                print "[!] Error loading inputfile"
                print e
            else:
                # load list cotent:
                listcontent = ["{0:d}:{1:s}".format(i + 1, repr(e))
                               for i, e in
                               enumerate(self.sourceselector.low_res_cat)]
                # set to first object
                self.selectinputcombobox['values'] = listcontent
                self.selectinputcombobox.current(0)
                self.display_input(0)

    def display_input(self, ind):
        self.sourceselector.load_object_by_ind(ind)
        self.sourceselector.load_display()
        self.sourceselector.show_hi_res_catalog()
        self.sourceselector.show_low_res_coord()
        self.sourceselector.ds9.set('raise')
        # show info in the lable
        label = """
low-res: {0:s}
------------------
obj#: {1:d}
map : {2:s}
RA  : {3:f}
Dec : {4:f}
pxsz: {5:.2f}"
beam: {6:s}

hi-res: {7:s}
------------------
map : {8:s}
""".format(self.sourceselector.low_res_label,
           ind + 1,
           self.sourceselector.low_res_map,
           self.sourceselector.low_res_coord[0],
           self.sourceselector.low_res_coord[1],
           self.sourceselector.low_res_ps,
           self.sourceselector.low_res_beamsize,
           self.sourceselector.hi_res_label,
           self.sourceselector.hi_res_map)
        self.displayinfo.set(label.strip())
        self.logfileinfo.set("logfile: {0:s}".format(
            self.sourceselector.galfit_logfile))

    def open_logfile(self):
        logfile = os.path.join(self.sourceselector.galfit_workroot,
                               self.sourceselector.galfit_work,
                               self.sourceselector.galfit_logfile)
        if os.path.isfile(logfile):
            webbrowser.open("file://" + logfile)
        else:
            print "[!] galfit logfile does not exist"

    def _add_tab(self, name):
        self.tab.append(ttk.Frame(master=self.notebook, name=name))
        self.tab[-1].pack(fill=Tkinter.BOTH, expand=1)
        #self.box.append(ScrolledTextScrolledText(master=self.tab[-1]))
        self.box.append(Tkinter.Text(master=self.tab[-1]))
        self.box[-1].pack(fill=Tkinter.BOTH, expand=1)
        self.notebook.add(self.tab[-1], text=name, underline=False)

    def _display_message(self, message):
        dest = {'coordinate': 0,
                'parfile': 1,
                'output': 2}
        i = dest[message[0]]
        j = message[1]
        self.box[i].delete('1.0', Tkinter.END)
        self.box[i].insert(Tkinter.END, j)
        self.notebook.select(i)

if __name__ == '__main__':
    gui = AdaptiveDeblendingUI()
    gui.mainloop()
