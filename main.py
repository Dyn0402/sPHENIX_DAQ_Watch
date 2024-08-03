#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on August 02 08:41 2024
Created in PyCharm
Created as sPHENIX_DAQ_Watch/main

@author: Dylan Neff, dn277127
"""

import tkinter as tk

from DAQWatchGUI import DAQWatchGUI


def main():
    root = tk.Tk()
    app = DAQWatchGUI(root)
    root.mainloop()
    print('donzo')


if __name__ == '__main__':
    main()
