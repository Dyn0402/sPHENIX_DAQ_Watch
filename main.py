#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on August 02 08:41 2024
Created in PyCharm
Created as sPHENIX_DAQ_Watch/main

@author: Dylan Neff, dn277127
"""

import sys
import tkinter as tk

from DAQWatchGUI import DAQWatchGUI


def main():
    local = False
    if len(sys.argv) > 2:
        print('Too many arguments.')
        return
    elif len(sys.argv) == 2:
        if sys.argv[1].lower() == 'local' or sys.argv[1].lower() == 'l' or sys.argv[1] == 1:
            local = True
    root = tk.Tk()
    app = DAQWatchGUI(root, local)
    root.mainloop()
    print('donzo')


if __name__ == '__main__':
    main()
