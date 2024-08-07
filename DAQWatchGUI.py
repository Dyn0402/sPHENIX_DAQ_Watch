#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on August 02 08:41 2024
Created in PyCharm
Created as sPHENIX_DAQ_Watch/DAQWatchGUI

@author: Dylan Neff, dn277127
"""

import os
import tkinter as tk
from tkinter import ttk
from tkinter import Toplevel, Button, Scrollbar, Text, filedialog, font
from threading import Thread
import json
from time import strftime, localtime, gmtime, sleep

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
from datetime import datetime

from DAQWatcher import DAQWatcher


class DAQWatchGUI:
    def __init__(self, root, local=False):
        self.root = root
        self.root.title("DAQ Watch")
        self.root.geometry('900x500')
        if local:
            self.grafana_url = 'http://localhost:7815'  # For running through forwarded ssh port
        else:
            self.grafana_url = 'http://insight.sphenix.bnl.gov:3000'  # For running through forwarded ssh port

        # Initialize parameter values
        self.rate_threshold = 100  # Hz Rate threshold to alert on
        self.integration_time = 10  # seconds Time over which to integrate rate. Must be integer
        self.check_time = 1  # seconds Time between checks
        self.target_run_time = 60  # minutes Targeted run time, alert when reached
        self.run_time_reminder = False  # Alert when target run time is reached
        self.mvtx_alerts = True  # Alert for MVTX mixed state staves
        self.new_run_cushion = 30  # seconds to wait after a new run starts before alerting on low rate
        self.rate_alarm_cushion = 2  # Require this many consecutive low rate checks before alerting

        self.repo_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_file_name = 'config.json'
        self.config_path = os.path.join(self.repo_dir, self.config_file_name)

        self.max_graph_points = 100000
        self.graph_points = 500

        self.silence = False

        self.previous_status = None
        self.previous_status_counter = 0
        self.status_refresh_count = 10

        self.alarm_sound_file_path = None
        self.run_end_reminder_sound_file_path = None
        self.run_start_sound_file_path = None
        self.mvtx_staves_alarm_sound_file_path = None

        # Create and place widgets
        self.create_widgets()

        # Load saved configuration
        self.load_config()

        self.watcher = DAQWatcher(update_callback=self.update_gui, rate_threshold=self.rate_threshold,
                                  integration_time=self.integration_time, check_time=self.check_time,
                                  target_run_time=self.target_run_time, grafana_url=self.grafana_url,
                                  new_run_cushion=self.new_run_cushion, rate_alarm_cushion=self.rate_alarm_cushion)
        self.watcher_thread = Thread(target=self.start_watcher)
        self.watcher_thread.daemon = True  # Daemonize thread so it stops with the GUI
        self.watcher_thread.name = 'Watcher Thread'
        self.watcher_thread.start()

        self.time_since_thread = Thread(target=self.update_time_since)
        self.time_since_thread.daemon = True
        self.time_since_thread.name = 'Time Since Thread'
        self.time_since_thread.start()

        self.set_parameters()
        self.set_sound_file_paths()

        self.update_param_display()

    def start_watcher(self):
        self.watcher.watch_daq()

    def create_widgets(self):
        style = ttk.Style()
        style.configure('TLabel', font=('Helvetica', 12))
        style.configure('TButton', font=('Helvetica', 12, 'bold'), padding=10)
        style.configure('TEntry', font=('Helvetica', 12), padding=5)

        form_button_status_frame = ttk.Frame(self.root)
        form_button_status_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=1)

        # Container frame for form elements
        form_frame = ttk.Frame(form_button_status_frame)
        form_frame.pack(side=tk.LEFT, fill=tk.X, padx=10, pady=10)

        # Rate label and entry
        self.rate_label = ttk.Label(form_frame, text="Rate Threshold (Hz):")
        self.rate_label.grid(column=0, row=0, padx=10, pady=2, sticky=tk.W)
        self.rate_value = ttk.Label(form_frame, width=5)
        self.rate_value.grid(column=1, row=0, padx=10, pady=2)
        self.rate_entry = ttk.Entry(form_frame, width=5)
        self.rate_entry.grid(column=2, row=0, padx=10, pady=2)

        # Integration time label and entry
        self.integration_time_label = ttk.Label(form_frame, text="Integration Time (s):")
        self.integration_time_label.grid(column=0, row=1, padx=10, pady=2, sticky=tk.W)
        self.intgration_time_value = ttk.Label(form_frame, width=5)
        self.intgration_time_value.grid(column=1, row=1, padx=10, pady=2)
        self.integration_time_entry = ttk.Entry(form_frame, width=5)
        self.integration_time_entry.grid(column=2, row=1, padx=10, pady=2)

        # Check time label and entry
        self.check_time_label = ttk.Label(form_frame, text="Check Time (s):")
        self.check_time_label.grid(column=0, row=2, padx=10, pady=2, sticky=tk.W)
        self.check_time_value = ttk.Label(form_frame, width=5)
        self.check_time_value.grid(column=1, row=2, padx=10, pady=2)
        self.check_time_entry = ttk.Entry(form_frame, width=5)
        self.check_time_entry.grid(column=2, row=2, padx=10, pady=2)

        # Target Run Time label and entry
        self.target_run_time_label = ttk.Label(form_frame, text="Target Run Time (min):")
        self.target_run_time_label.grid(column=0, row=3, padx=10, pady=2, sticky=tk.W)
        self.target_run_time_value = ttk.Label(form_frame, width=5)
        self.target_run_time_value.grid(column=1, row=3, padx=10, pady=2)
        self.target_run_time_entry = ttk.Entry(form_frame, width=5)
        self.target_run_time_entry.grid(column=2, row=3, padx=10, pady=2)

        # Alarm points cushion label and entry
        self.rate_alarm_cushion_label = ttk.Label(form_frame, text="Alarm Points Cushion:")
        self.rate_alarm_cushion_label.grid(column=0, row=4, padx=10, pady=2, sticky=tk.W)
        self.rate_alarm_cushion_value = ttk.Label(form_frame, width=5)
        self.rate_alarm_cushion_value.grid(column=1, row=4, padx=10, pady=2)
        self.rate_alarm_cushion_entry = ttk.Entry(form_frame, width=5)
        self.rate_alarm_cushion_entry.grid(column=2, row=4, padx=10, pady=2)

        # New run cushion label and entry
        self.new_run_cushion_label = ttk.Label(form_frame, text="New Run Cushion (s):")
        self.new_run_cushion_label.grid(column=0, row=5, padx=10, pady=2, sticky=tk.W)
        self.new_run_cushion_value = ttk.Label(form_frame, width=5)
        self.new_run_cushion_value.grid(column=1, row=5, padx=10, pady=2)
        self.new_run_cushion_entry = ttk.Entry(form_frame, width=5)
        self.new_run_cushion_entry.grid(column=2, row=5, padx=10, pady=2)

        # Graph points label and entry
        self.graph_points_label = ttk.Label(form_frame, text="Graph Points:")
        self.graph_points_label.grid(column=0, row=6, padx=10, pady=2, sticky=tk.W)
        self.graph_points_value = ttk.Label(form_frame, width=5)
        self.graph_points_value.grid(column=1, row=6, padx=10, pady=2)
        self.graph_points_entry = ttk.Entry(form_frame, width=5)
        self.graph_points_entry.grid(column=2, row=6, padx=10, pady=2)

        # Button frame for buttons
        button_frame = ttk.Frame(form_button_status_frame)
        # button_frame.grid(column=0, row=3, columnspan=2, pady=10)
        button_frame.pack(side=tk.LEFT, fill=tk.X, padx=40, pady=10)

        # Set button
        self.set_button = tk.Button(button_frame, text="Set Config", command=self.set_parameters, bg='gray', fg='white',
                                    font=('Helvetica', 13, 'bold'), relief=tk.RAISED, bd=2, width=9)
        self.set_button.pack(side=tk.TOP, pady=4)

        # Save button
        self.save_button = tk.Button(button_frame, text="Save Config", command=self.save_config, bg='gray',
                                     fg='white', font=('Helvetica', 13, 'bold'), relief=tk.RAISED, bd=2, width=9)
        self.save_button.pack(side=tk.TOP, pady=4)

        # Silence button
        self.silence_button = tk.Button(button_frame, text="Silence", command=self.silence_click, bg='#3c8dbc', fg='white',
                                        font=('Helvetica', 15, 'bold'), relief=tk.RAISED, bd=2, width=9)
        self.silence_button.pack(side=tk.TOP, pady=4)

        # Checkbox for run time reminder
        self.run_time_reminder_var = tk.IntVar()
        self.run_time_reminder_var.set(self.run_time_reminder)
        self.run_time_reminder_check = ttk.Checkbutton(button_frame, text="Run Time Reminder",
                                                       variable=self.run_time_reminder_var)
        self.run_time_reminder_check.pack(side=tk.TOP, pady=3)

        # Checkbox for mvtx alarms
        self.mvtx_alarm_var = tk.IntVar()
        self.mvtx_alarm_var.set(self.mvtx_alerts)
        self.mvtx_alarm_check = ttk.Checkbutton(button_frame, text="MVTX Staves Alarm",
                                                variable=self.mvtx_alarm_var)
        self.mvtx_alarm_check.pack(side=tk.TOP, pady=3)

        # Readme button, make smaller and less exciting than other buttons
        self.readme_button = tk.Button(button_frame, text="Readme", command=self.show_readme, bg='lightgrey',
                                       fg='black', font=('Helvetica', 10, 'bold'), relief=tk.RAISED, bd=2)
        self.readme_button.pack(side=tk.TOP, pady=2)

        # Sound control window button
        self.sound_control_window_button = tk.Button(button_frame, text="Sound Control",
                                                     command=self.show_sound_control, bg='lightgrey', fg='black',
                                                     font=('Helvetica', 10, 'bold'), relief=tk.RAISED, bd=2)
        self.sound_control_window_button.pack(side=tk.TOP, pady=2)

        output_frame = ttk.Frame(form_button_status_frame)
        output_frame.pack(side=tk.RIGHT, fill=tk.X, padx=10, pady=10)

        run_status_frame = ttk.Frame(output_frame)
        run_status_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        # Date and time display
        self.date_time_label = ttk.Label(run_status_frame, text="Last Check:")
        self.date_time_label.grid(column=0, row=0, padx=10, pady=6, sticky=tk.W)
        self.date_time = ttk.Label(run_status_frame, text=strftime("%m-%d %H:%M:%S", localtime()),
                                      font=('Helvetica', 14, 'bold'))
        self.date_time.grid(column=1, row=0, padx=10, pady=6)

        # Time since last check display
        self.time_since_label = ttk.Label(run_status_frame, text="Last Checked:")
        self.time_since_label.grid(column=0, row=1, padx=10, pady=6, sticky=tk.W)
        self.time_since = ttk.Label(run_status_frame, text="N/A", font=('Helvetica', 14, 'bold'))
        self.time_since.grid(column=1, row=1, padx=10, pady=6)

        # Run num display
        self.run_num_label = ttk.Label(run_status_frame, text="Run Number:")
        self.run_num_label.grid(column=0, row=2, padx=10, pady=6, sticky=tk.W)
        self.run_num = ttk.Label(run_status_frame, text="N/A", font=('Helvetica', 14, 'bold'))
        self.run_num.grid(column=1, row=2, padx=10, pady=6)

        # Run time display
        self.run_time_label = ttk.Label(run_status_frame, text="Run Time:")
        self.run_time_label.grid(column=0, row=3, padx=10, pady=6, sticky=tk.W)
        self.run_time = ttk.Label(run_status_frame, text="N/A", font=('Helvetica', 14, 'bold'))
        self.run_time.grid(column=1, row=3, padx=10, pady=6)

        # MVTX Mixed Staves display
        self.mvtx_mixed_staves_label = ttk.Label(run_status_frame, text="Mixed Staves:")
        self.mvtx_mixed_staves_label.grid(column=0, row=4, padx=10, pady=6, sticky=tk.W)
        self.mvtx_mixed_staves = ttk.Label(run_status_frame, text="N/A", font=('Helvetica', 14, 'bold'))
        self.mvtx_mixed_staves.grid(column=1, row=4, padx=10, pady=6)

        # Rate display
        self.rate_display_label = ttk.Label(run_status_frame, text="Current Rate:")
        self.rate_display_label.grid(column=0, row=5, padx=10, pady=6, sticky=tk.W)
        self.rate_display = ttk.Label(run_status_frame, text="N/A", font=('Helvetica', 14, 'bold'))
        self.rate_display.grid(column=1, row=5, padx=10, pady=6)

        # Status label
        self.status_label = ttk.Label(output_frame, text="Status: Running", anchor='center',
                                      font=('Helvetica', 12, 'italic'))
        self.status_label.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        # Container frame for the graph
        graph_frame = ttk.Frame(self.root)
        graph_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Rate plot
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.time_data = []
        self.rate_data = []
        self.line, = self.ax.plot([], [], 'r-')
        self.thresh_line = self.ax.axhline(self.rate_threshold / 1000, color='g', linestyle='--')

        # Format x-axis as time
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))

        # Match the plot background to Tkinter window background
        bg_color = self.root.cget('bg')
        self.ax.set_facecolor(bg_color)
        self.fig.patch.set_facecolor(bg_color)

        self.ax.set_ylabel('DAQ Rate (kHz)')
        self.fig.subplots_adjust(left=0.081, right=0.98, top=0.99, bottom=0.1)

    def save_config(self):
        config = {
            'rate_threshold': self.rate_entry.get(),
            'integration_time': self.integration_time_entry.get(),
            'check_time': self.check_time_entry.get(),
            'target_run_time': self.target_run_time_entry.get(),
            'rate_alarm_cushion': self.rate_alarm_cushion_entry.get(),
            'new_run_cushion': self.new_run_cushion_entry.get(),
            'graph_points': self.graph_points_entry.get(),
            'run_time_reminder': self.run_time_reminder_var.get(),
            'mvtx_staves_alarm': self.mvtx_alarm_var.get(),
            'alarm_sound_file': self.alarm_sound_file_path,
            'run_end_reminder_sound_file': self.run_end_reminder_sound_file_path,
            'run_start_sound_file': self.run_start_sound_file_path,
            'mvtx_staves_alarm_sound_file': self.mvtx_staves_alarm_sound_file_path
        }
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=4)
        # print("Configuration saved.")
        self.status_label.config(text="Configuration saved", foreground='black')

    def load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                self.rate_entry.insert(0, config.get('rate_threshold', ''))
                self.integration_time_entry.insert(0, config.get('integration_time', ''))
                self.check_time_entry.insert(0, config.get('check_time', ''))
                self.target_run_time_entry.insert(0, config.get('target_run_time', ''))
                self.rate_alarm_cushion_entry.insert(0, config.get('rate_alarm_cushion', ''))
                self.new_run_cushion_entry.insert(0, config.get('new_run_cushion', ''))
                self.graph_points_entry.insert(0, config.get('graph_points', ''))
                self.run_time_reminder_var.set(config.get('run_time_reminder', 0))
                self.mvtx_alarm_var.set(config.get('mvtx_staves_alarm', 0))
                self.alarm_sound_file_path = config.get('alarm_sound_file', None)
                self.run_end_reminder_sound_file_path = config.get('run_end_reminder_sound_file', None)
                self.run_start_sound_file_path = config.get('run_start_sound_file', None)
                self.mvtx_staves_alarm_sound_file_path = config.get('mvtx_staves_alarm_sound_file', None)
            self.status_label.config(text="Configuration loaded", foreground='black')
        except FileNotFoundError:
            # print("No configuration file found.")
            self.status_label.config(text="No configuration file found.", foreground='black')

    def update_param_display(self):
        self.rate_value.config(text=self.watcher.rate_threshold)
        self.intgration_time_value.config(text=self.watcher.integration_time)
        self.check_time_value.config(text=self.watcher.check_time)
        self.target_run_time_value.config(text=self.watcher.target_run_time)
        self.rate_alarm_cushion_value.config(text=self.watcher.rate_alarm_cushion)
        self.new_run_cushion_value.config(text=self.watcher.new_run_cushion)
        self.graph_points_value.config(text=self.graph_points)
        self.run_time_reminder_var.set(self.run_time_reminder)
        self.mvtx_alarm_var.set(self.mvtx_alerts)

    def update_time_since(self):
        while True:
            # Get last check from self.date_time and convert to datetime object
            last_check_str = self.date_time.cget('text')
            last_check = datetime.strptime(last_check_str, "%m-%d %H:%M:%S")
            # Set last_check to current year
            last_check = last_check.replace(year=datetime.now().year)
            time_since = datetime.now() - last_check

            # Update time_since label in number of seconds since last check
            num_seconds = time_since.total_seconds()
            if num_seconds < 60:
                time_since_str = f"{num_seconds:.0f} sec ago"
            elif num_seconds < 3600:
                time_since_str = f"{num_seconds / 60:.0f} min ago"
            elif num_seconds < 86400:
                time_since_str = f"{num_seconds / 3600:.0f} hr ago"
            else:
                time_since_str = f"{num_seconds / 86400:.0f} days ago"
            self.time_since.config(text=time_since_str)
            sleep(10)

    def set_parameters(self):
        set_rate_threshold = self.rate_entry.get()
        if set_rate_threshold != '':
            self.rate_threshold = float(set_rate_threshold)
            self.watcher.rate_threshold = self.rate_threshold

        set_integration_time = self.integration_time_entry.get()
        if set_integration_time != '':
            self.integration_time = int(set_integration_time)
            self.watcher.integration_time = self.integration_time

        set_check_time = self.check_time_entry.get()
        if set_check_time != '':
            self.check_time = float(set_check_time)
            self.watcher.check_time = self.check_time

        set_target_run_time = self.target_run_time_entry.get()
        if set_target_run_time != '':
            self.target_run_time = float(set_target_run_time)
            self.watcher.target_run_time = self.target_run_time

        set_rate_alarm_cushion = self.rate_alarm_cushion_entry.get()
        if set_rate_alarm_cushion != '':
            self.rate_alarm_cushion = int(set_rate_alarm_cushion)
            self.watcher.rate_alarm_cushion = self.rate_alarm_cushion

        set_new_run_cushion = self.new_run_cushion_entry.get()
        if set_new_run_cushion != '':
            self.new_run_cushion = float(set_new_run_cushion)
            self.watcher.new_run_cushion = self.new_run_cushion

        set_graph_points = self.graph_points_entry.get()
        if set_graph_points != '':
            self.graph_points = int(set_graph_points)
            self.watcher.graph_points = self.graph_points

        self.run_time_reminder = self.run_time_reminder_var.get()
        self.watcher.run_time_reminder = self.run_time_reminder

        self.mvtx_alerts = self.mvtx_alarm_var.get()
        self.watcher.mvtx_alerts = self.mvtx_alerts

        # print(f"Parameters set: Rate Threshold={self.rate_threshold}, Integration Time={self.integration_time}, "
        #       f"Check Time={self.check_time}, Target Run Time={self.target_run_time}, "
        #       f"Run Time Reminder={self.run_time_reminder}")

        self.update_param_display()
        self.status_label.config(text="Parameters Set", foreground='black')

    def set_sound_file_paths(self):
        """
        Set DAQWatcher sound files paths from DAQWatchGUI values
        :return:
        """
        if self.alarm_sound_file_path is not None:
            self.watcher.alert_sound_file = self.alarm_sound_file_path
        if self.run_end_reminder_sound_file_path is not None:
            self.watcher.run_end_sound_file = self.run_end_reminder_sound_file_path
        if self.run_start_sound_file_path is not None:
            self.watcher.run_start_sound_file = self.run_start_sound_file_path
        if self.mvtx_staves_alarm_sound_file_path is not None:
            self.watcher.mvtx_alert_sound_file = self.mvtx_staves_alarm_sound_file_path

    def silence_click(self):
        self.silence = not self.silence
        if self.silence:
            self.silence_button.config(bg='red', text='Unsilence')
        else:
            self.silence_button.config(bg='#3c8dbc', text='Silence')
        self.watcher.silence = self.silence
        self.status_label.config(text="Alarm silenced" if self.silence else "Alarm Unsilenced")

    def update_gui(self, run_num, rate, run_time, mvtx_mixed_staves, mvtx_new_mixed_staves,
                   rate_alert, run_time_alert, mvtx_alert, junk, new_run=False):
        refresh_time = datetime.now()
        refresh_time_str = refresh_time.strftime("%m-%d %H:%M:%S")
        self.date_time.config(text=refresh_time_str)

        if run_time is None:
            self.run_time.config(text="Not Running")
        else:
            run_time_str = strftime("%H:%M:%S", gmtime(run_time))
            self.run_time.config(text=run_time_str)

        if mvtx_mixed_staves is None:
            self.mvtx_mixed_staves.config(text="N/A")
            self.mvtx_mixed_staves.config(foreground='black')
        else:
            self.mvtx_mixed_staves.config(text=mvtx_mixed_staves)
            if mvtx_mixed_staves == 0:
                self.mvtx_mixed_staves.config(foreground='green', font=('Helvetica', 14, 'bold'))
            elif mvtx_mixed_staves == 1:
                self.mvtx_mixed_staves.config(foreground='#a0a500', font=('Helvetica', 18, 'bold'))
            elif mvtx_mixed_staves > 1:
                self.mvtx_mixed_staves.config(foreground='red', font=('Helvetica', 18, 'bold'))
            else:
                self.mvtx_mixed_staves.config(foreground='black', font=('Helvetica', 14, 'bold'))

        if run_num is None:
            self.run_num.config(text="Not Running")
        else:
            self.run_num.config(text=run_num)
            if new_run:
                self.status_label.config(text=f"New run {run_num} started", foreground='blue',
                                         font=('Helvetica', 12, 'italic'))

        if rate is None:
            self.rate_display.config(text="Not Running")
            y_top = None
        else:
            self.rate_display.config(text=f"{rate / 1000:.2f} kHz")
            self.time_data.append(refresh_time)
            self.rate_data.append(rate / 1000)
            y_top = max(max(self.rate_data), self.rate_threshold / 1000) * 1.1

        # Update graph data
        self.time_data = self.time_data[-self.max_graph_points:]  # Keep only the last n data points
        self.rate_data = self.rate_data[-self.max_graph_points:]

        self.line.set_data(self.time_data[-self.graph_points:], self.rate_data[-self.graph_points:])
        self.thresh_line.set_ydata([self.rate_threshold / 1000, self.rate_threshold / 1000])
        if y_top is not None and y_top > 0:
            self.ax.set_ylim(0, y_top)
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()

        if self.status_label.cget('text') != self.previous_status:
            self.previous_status = self.status_label.cget('text')
            self.previous_status_counter = 0
        else:
            self.previous_status_counter += 1

        rate_alert_mesg, run_time_alert_mesg, junk_run_mesg = "Low Rate!", "Target Run Time Reached", "Junk Run"
        if junk:
            self.status_label.config(text=junk_run_mesg, foreground='gray', font=('Helvetica', 12, 'italic'))
        elif rate_alert:
            self.status_label.config(text=rate_alert_mesg, foreground='red', font=('Helvetica', 14, 'bold'))
        elif mvtx_alert:
            self.status_label.config(text="Recover MVTX Mixed State Staves!", foreground='red',
                                     font=('Helvetica', 12, 'bold'))
        elif run_time_alert:
            self.status_label.config(text=run_time_alert_mesg, foreground='green', font=('Helvetica', 12, 'italic'))
        elif mvtx_new_mixed_staves > 0:
            self.status_label.config(text=f"New MVTX Mixed Stave: {mvtx_new_mixed_staves}", foreground='#FF8C00',
                                     font=('Helvetica', 12, 'italic'))
        else:  # If status_label text is either of the alert messages, change it back to ""
            # if self.status_label.cget('text') in [rate_alert_mesg, run_time_alert_mesg, junk_run_mesg]:
            #     self.status_label.config(text="", foreground='black')
            if (self.previous_status_counter > self.status_refresh_count or
                    self.status_label.cget('text') == rate_alert_mesg):
                if rate is not None and rate >= self.rate_threshold:
                    self.status_label.config(text="Running", foreground='green', font=('Helvetica', 12, 'italic'))
                else:
                    self.status_label.config(text="Not Running", foreground='black', font=('Helvetica', 12, 'italic'))

    def show_sound_control(self):
        """
        Create pop up window with sound control options. A label for each of the two sound file paths
        (alarm and run end) along with a button for each which opens a Linux file explorer to select a new file.
        In addition, a button to play the current alarm sound.
        :return:
        """
        # Create the pop-up window
        sound_control_window = Toplevel(self.root)
        sound_control_window.title("Sound Control")
        sound_control_window.geometry("1000x600")
        sound_control_window.configure(bg="#2E2E2E")

        # Custom fonts
        title_font = font.Font(family="Helvetica", size=18, weight="bold")
        label_font = font.Font(family="Helvetica", size=14)
        button_font = font.Font(family="Helvetica", size=14, weight="bold")

        # Label explaining the purpose of the window
        sound_control_label = ttk.Label(sound_control_window,
                                        text="Select sound files for alarms. This hasn't really been tested...",
                                        font=title_font, background="#2E2E2E", foreground="#FFFFFF")
        sound_control_label.grid(row=0, column=0, columnspan=3, pady=20)

        # Add extra space after 0th row
        sound_control_window.grid_rowconfigure(1, minsize=20)

        # Alarm sound label and button
        alarm_sound_label = ttk.Label(sound_control_window, text="Alarm Sound:", font=label_font, background="#2E2E2E",
                                      foreground="#FFFFFF")
        alarm_sound_label.grid(row=2, column=0, pady=10, padx=10, sticky="W")
        self.alarm_path_label = ttk.Label(sound_control_window, text=self.watcher.alert_sound_file, font=label_font,
                                          background="#2E2E2E", foreground="#FFFFFF")
        self.alarm_path_label.grid(row=2, column=1, pady=10, padx=10)
        alarm_sound_button = ttk.Button(sound_control_window, text="Select Alarm Sound",
                                        command=self.select_alarm_sound)
        alarm_sound_button.grid(row=3, column=0, pady=10, padx=10)
        alarm_sound_play_button = ttk.Button(sound_control_window, text="Play Alarm Sound", command=lambda: os.system(
            f'aplay {self.watcher.alert_sound_file} > /dev/null 2>&1'))
        alarm_sound_play_button.grid(row=3, column=1, pady=10, padx=10)

        # Add extra space after 2nd row
        sound_control_window.grid_rowconfigure(4, minsize=40)

        # Run end sound label and button
        run_end_sound_label = ttk.Label(sound_control_window, text="Run End Sound:", font=label_font,
                                        background="#2E2E2E", foreground="#FFFFFF")
        run_end_sound_label.grid(row=5, column=0, pady=10, padx=10, sticky="W")
        self.run_end_path_label = ttk.Label(sound_control_window, text=self.watcher.run_end_sound_file, font=label_font,
                                            background="#2E2E2E", foreground="#FFFFFF")
        self.run_end_path_label.grid(row=5, column=1, pady=10, padx=10)
        run_end_sound_button = ttk.Button(sound_control_window, text="Select Run End Sound",
                                          command=self.select_run_end_sound)
        run_end_sound_button.grid(row=6, column=0, pady=10, padx=10)
        run_end_sound_play_button = ttk.Button(sound_control_window, text="Play Run End Sound",
                                               command=lambda: os.system(
                                                   f'aplay {self.watcher.run_end_sound_file} > /dev/null 2>&1'))
        run_end_sound_play_button.grid(row=6, column=1, pady=10, padx=10)

        # Add extra space after 5th row
        sound_control_window.grid_rowconfigure(7, minsize=40)

        run_start_sound_label = ttk.Label(sound_control_window, text="Run Start Sound:", font=label_font,
                                            background="#2E2E2E", foreground="#FFFFFF")
        run_start_sound_label.grid(row=8, column=0, pady=10, padx=10, sticky="W")
        self.run_start_path_label = ttk.Label(sound_control_window, text=self.watcher.run_start_sound_file, font=label_font,
                                                background="#2E2E2E", foreground="#FFFFFF")
        self.run_start_path_label.grid(row=8, column=1, pady=10, padx=10)
        run_start_sound_button = ttk.Button(sound_control_window, text="Select Run Start Sound",
                                            command=self.select_run_start_sound)
        run_start_sound_button.grid(row=9, column=0, pady=10, padx=10)
        run_start_sound_play_button = ttk.Button(sound_control_window, text="Play Run Start Sound",
                                                command=lambda: os.system(
                                                    f'aplay {self.watcher.run_start_sound_file} > /dev/null 2>&1'))
        run_start_sound_play_button.grid(row=9, column=1, pady=10, padx=10)

        # Add extra space after 7th row
        sound_control_window.grid_rowconfigure(10, minsize=40)

        mvtx_staves_alarm_sound_label = ttk.Label(sound_control_window, text="MVTX Staves Alarm Sound:", font=label_font,
                                                background="#2E2E2E", foreground="#FFFFFF")
        mvtx_staves_alarm_sound_label.grid(row=11, column=0, pady=10, padx=10, sticky="W")
        self.mvtx_staves_alarm_path_label = ttk.Label(sound_control_window, text=self.watcher.mvtx_alert_sound_file, font=label_font,
                                                    background="#2E2E2E", foreground="#FFFFFF")
        self.mvtx_staves_alarm_path_label.grid(row=11, column=1, pady=10, padx=10)
        mvtx_staves_alarm_sound_button = ttk.Button(sound_control_window, text="Select MVTX Staves Alarm Sound",
                                                    command=self.select_mvtx_staves_alarm_sound)
        mvtx_staves_alarm_sound_button.grid(row=12, column=0, pady=10, padx=10)
        mvtx_staves_alarm_sound_play_button = ttk.Button(sound_control_window, text="Play MVTX Staves Alarm Sound",
                                                        command=lambda: os.system(
                                                            f'aplay {self.watcher.mvtx_alert_sound_file} > /dev/null 2>&1'))
        mvtx_staves_alarm_sound_play_button.grid(row=12, column=1, pady=10, padx=10)

        # Add extra space after 12th row
        sound_control_window.grid_rowconfigure(13, minsize=40)

        # Add a close button
        close_button = ttk.Button(sound_control_window, text="Close", command=sound_control_window.destroy)
        close_button.grid(row=14, column=1, pady=20, padx=10)

        # Style the buttons
        style = ttk.Style()
        style.configure("TButton", font=button_font, padding=6, relief="flat", background="#4CAF50",
                        foreground="#FFFFFF", borderwidth=2)
        style.map("TButton", background=[("active", "#45A049")])
        style.configure("TButton", borderwidth=2, relief="flat", bordercolor="#4CAF50")

        # Add padding to all widgets
        for child in sound_control_window.winfo_children():
            child.grid_configure(padx=10, pady=5)

    def select_alarm_sound(self):
        """
        Open a file explorer to select a new alarm sound file.
        :return:
        """
        alarm_sound_file = filedialog.askopenfilename(initialdir="/", title="Select Alarm Sound",
                                                      filetypes=(("wav files", "*.wav"), ("all files", "*.*")))
        if alarm_sound_file:
            self.watcher.alert_sound_file = alarm_sound_file
            self.alarm_path_label.config(text=alarm_sound_file)
            self.status_label.config(text=f"Alarm sound file set", foreground='black')

    def select_run_end_sound(self):
        """
        Open a file explorer to select a new run end sound file.
        :return:
        """
        run_end_sound_file = filedialog.askopenfilename(initialdir="/", title="Select Run End Sound",
                                                        filetypes=(("wav files", "*.wav"), ("all files", "*.*")))
        if run_end_sound_file:
            self.watcher.run_end_sound_file = run_end_sound_file
            self.run_end_path_label.config(text=run_end_sound_file)
            self.status_label.config(text=f"Run end sound file set", foreground='black')

    def select_run_start_sound(self):
        """
        Open a file explorer to select a new run start sound file.
        :return:
        """
        run_start_sound_file = filedialog.askopenfilename(initialdir="/", title="Select Run Start Sound",
                                                        filetypes=(("wav files", "*.wav"), ("all files", "*.*")))
        if run_start_sound_file:
            self.watcher.run_start_sound_file = run_start_sound_file
            self.run_start_path_label.config(text=run_start_sound_file)
            self.status_label.config(text=f"Run start sound file set", foreground='black')

    def select_mvtx_staves_alarm_sound(self):
        """
        Open a file explorer to select a new MVTX staves alarm sound file.
        :return:
        """
        mvtx_staves_alarm_sound_file = filedialog.askopenfilename(initialdir="/", title="Select MVTX Staves Alarm Sound",
                                                        filetypes=(("wav files", "*.wav"), ("all files", "*.*")))
        if mvtx_staves_alarm_sound_file:
            self.watcher.mvtx_alert_sound_file = mvtx_staves_alarm_sound_file
            self.mvtx_staves_alarm_path_label.config(text=mvtx_staves_alarm_sound_file)
            self.status_label.config(text=f"MVTX staves alarm sound file set", foreground='black')

    def show_readme(self):
        # Create the pop-up window
        readme_window = Toplevel(self.root)
        readme_window.title("Readme")
        readme_window.geometry("700x500")

        # Add a scrollbar
        scrollbar = Scrollbar(readme_window)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Add a Text widget with a scrollbar
        readme_text_widget = Text(readme_window, wrap='word', yscrollcommand=scrollbar.set, font=('Helvetica', 12),
                                  padx=10, pady=10)
        readme_text_widget.pack(expand=True, fill=tk.BOTH)
        scrollbar.config(command=readme_text_widget.yview)

        # Apply tags for bold and bullet points
        readme_text_widget.tag_configure('bold', font=('Helvetica', 12, 'bold'))
        readme_text_widget.tag_configure('bullet', font=('Helvetica', 12))

        # Insert the readme text into the Text widget
        readme_text = """
This application monitors the DAQ rate from the Prometheus database via a Grafana proxy API call. It polls the database every 'check_time' seconds and retrieves the current run number and DAQ rate, averaged over the past 'integration_time' seconds. If the rate falls below the specified threshold, an alarm will sound. This is particularly helpful for quickly alerting the shift crew to seb hangs as well as beam aborts. Thanks to Cameron it now also monitors the number of MVTX staves in a mixed state and alerts when action is required.

"""
        readme_text_widget.insert(tk.END, readme_text)

        # Add bold and bullet text
        parameters = [
            "Rate Threshold (Hz): An audible alarm will sound if the rate falls below this value. Put slightly above zero to catch beam aborts (residual rate of around 100Hz for a few seconds).",
            "Integration Time (s): The time period over which the rate is averaged. Increasing reduces false alarms but delays alarm time for true DAQ stalls.",
            "Check Time (s): The interval between each database poll. Database updated every 2 seconds, so no need to poll more frequently than every 1 or 2 seconds. Times much longer than this will delay alarm in case of true DAQ stall.",
            "Target Run Time (min): The targeted max time for each run. Only used if 'Run Time Reminder' is enabled.",
            "Alarm Points Cushion: The number of consecutive low rate reads required before sounding the alarm. 1 will sound the alarm on the first low rate read. Probably keep at 1 if false positive rate low, else 2 should be ok. The larger this is the further delayed a true alarm will be.",
            "New Run Cushion (s): The time to wait after a new run starts before alerting on low rate. ~10-30 seconds should be fine.",
            "Graph Points: The number of points to display on the rate plot.",
        ]

        readme_text_widget.insert(tk.END, "Parameters:\n", 'bold')
        for item in parameters:
            readme_text_widget.insert(tk.END, f"  • {item}\n", 'bullet')

        readme_text_widget.insert(tk.END, "\nButtons:\n", 'bold')
        buttons = [
            "Set: Apply the input parameters.",
            "Save Config: Save the current configuration to a file. These values will be loaded on next start of the GUI.",
            "Silence/Unsilence: Mute or unmute the alarm.",
            "Run Time Reminder: Option to alert when the target run time is reached to remind the user to start a new run.",
            "MVTX Staves Alarm: Option to alert when there are MVTX staves in a mixed state. If only one, alarms after run. If more than one, alarms immediately.",
            "Readme: Display this readme.",
            "Sound Control: Open a window to select sound files for the alarm and run end alerts. Not really tested..."
        ]
        for item in buttons:
            readme_text_widget.insert(tk.END, f"  • {item}\n", 'bullet')

        readme_text_widget.insert(tk.END, "\nStatus and Plot:\n", 'bold')
        status_parameters = [
            "Last Check: Displays the timestamp of the last time the database was polled. Should be current time.",
            "Last Checked: Shows the time since the last check. Updates every 10 seconds.",
            "Run Number: Shows the current run number.",
            "Run Time: Indicates the elapsed time for the current run. Only starts counting once the GUI has been opened.",
            "Mixed Staves: Displays the number of MVTX staves currently in a mixed state.",
            "Current Rate: Displays the current DAQ rate.",
            "Rate Plot: A graph showing the DAQ rate over time, updated with each check."
        ]
        for item in status_parameters:
            readme_text_widget.insert(tk.END, f"  • {item}\n", 'bullet')

        readme_text_widget.insert(tk.END,
                                  "\nCurrently only working on Linux systems with the 'aplay' command available.\n",
                                  'bold')
        readme_text_widget.insert(tk.END, "For questions or issues, please contact Dylan Neff (dneff@ucla.edu)")

        # Disable editing the readme text
        readme_text_widget.config(state=tk.DISABLED)

        # Add a close button
        close_button = Button(readme_window, text="Close", command=readme_window.destroy)
        close_button.pack(pady=10)

