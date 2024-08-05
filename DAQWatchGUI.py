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
from tkinter import Toplevel, Button, Scrollbar, Text
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
        self.new_run_cushion = 30  # seconds to wait after a new run starts before alerting on low rate
        self.rate_alarm_cushion = 2  # Require this many consecutive low rate checks before alerting

        self.repo_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_file_name = 'config.json'
        self.config_path = os.path.join(self.repo_dir, self.config_file_name)

        self.graph_points = 500

        self.silence = False

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
        self.set_button.pack(side=tk.TOP, pady=7)

        # Save button
        self.save_button = tk.Button(button_frame, text="Save Config", command=self.save_config, bg='gray',
                                     fg='white', font=('Helvetica', 13, 'bold'), relief=tk.RAISED, bd=2, width=9)
        self.save_button.pack(side=tk.TOP, pady=7)

        # Silence button
        self.silence_button = tk.Button(button_frame, text="Silence", command=self.silence_click, bg='#3c8dbc', fg='white',
                                        font=('Helvetica', 15, 'bold'), relief=tk.RAISED, bd=2, width=9)
        self.silence_button.pack(side=tk.TOP, pady=7)

        # Checkbox for run time reminder
        self.run_time_reminder_var = tk.IntVar()
        self.run_time_reminder_var.set(self.run_time_reminder)
        self.run_time_reminder_check = ttk.Checkbutton(button_frame, text="Run Time Reminder",
                                                       variable=self.run_time_reminder_var)
        self.run_time_reminder_check.pack(side=tk.TOP, pady=7)

        # Readme button, make smaller and less exciting than other buttons
        self.readme_button = tk.Button(button_frame, text="Readme", command=self.show_readme, bg='lightgrey',
                                       fg='black', font=('Helvetica', 10, 'bold'), relief=tk.RAISED, bd=2)
        self.readme_button.pack(side=tk.TOP, pady=7)

        output_frame = ttk.Frame(form_button_status_frame)
        output_frame.pack(side=tk.RIGHT, fill=tk.X, padx=10, pady=10)

        run_status_frame = ttk.Frame(output_frame)
        run_status_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        # Date and time display
        self.date_time_label = ttk.Label(run_status_frame, text="Last Check:")
        self.date_time_label.grid(column=0, row=0, padx=10, pady=9, sticky=tk.W)
        self.date_time = ttk.Label(run_status_frame, text=strftime("%m-%d %H:%M:%S", localtime()),
                                      font=('Helvetica', 14, 'bold'))
        self.date_time.grid(column=1, row=0, padx=10, pady=9)

        # Time since last check display
        self.time_since_label = ttk.Label(run_status_frame, text="Last Checked:")
        self.time_since_label.grid(column=0, row=1, padx=10, pady=9, sticky=tk.W)
        self.time_since = ttk.Label(run_status_frame, text="N/A", font=('Helvetica', 14, 'bold'))
        self.time_since.grid(column=1, row=1, padx=10, pady=9)

        # Run num display
        self.run_num_label = ttk.Label(run_status_frame, text="Run Number:")
        self.run_num_label.grid(column=0, row=2, padx=10, pady=9, sticky=tk.W)
        self.run_num = ttk.Label(run_status_frame, text="N/A", font=('Helvetica', 14, 'bold'))
        self.run_num.grid(column=1, row=2, padx=10, pady=9)

        # Run time display
        self.run_time_label = ttk.Label(run_status_frame, text="Run Time:")
        self.run_time_label.grid(column=0, row=3, padx=10, pady=9, sticky=tk.W)
        self.run_time = ttk.Label(run_status_frame, text="N/A", font=('Helvetica', 14, 'bold'))
        self.run_time.grid(column=1, row=3, padx=10, pady=9)

        # Rate display
        self.rate_display_label = ttk.Label(run_status_frame, text="Current Rate:")
        self.rate_display_label.grid(column=0, row=4, padx=10, pady=9, sticky=tk.W)
        self.rate_display = ttk.Label(run_status_frame, text="N/A", font=('Helvetica', 14, 'bold'))
        self.rate_display.grid(column=1, row=4, padx=10, pady=9)

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
            'run_time_reminder': self.run_time_reminder_var.get()
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
            sleep(1)

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

        # print(f"Parameters set: Rate Threshold={self.rate_threshold}, Integration Time={self.integration_time}, "
        #       f"Check Time={self.check_time}, Target Run Time={self.target_run_time}, "
        #       f"Run Time Reminder={self.run_time_reminder}")

        self.update_param_display()
        self.status_label.config(text="Parameters Set", foreground='black')

    def silence_click(self):
        self.silence = not self.silence
        if self.silence:
            self.silence_button.config(bg='red', text='Unsilence')
        else:
            self.silence_button.config(bg='#3c8dbc', text='Silence')
        self.watcher.silence = self.silence
        self.status_label.config(text="Alarm silenced" if self.silence else "Alarm Unsilenced")

    def update_gui(self, run_num, rate, run_time, rate_alert, run_time_alert, junk, new_run=False):
        refresh_time = datetime.now()
        refresh_time_str = refresh_time.strftime("%m-%d %H:%M:%S")
        self.date_time.config(text=refresh_time_str)

        if run_time is None:
            self.run_time.config(text="Not Running")
        else:
            run_time_str = strftime("%H:%M:%S", gmtime(run_time))
            self.run_time.config(text=run_time_str)

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
        self.time_data = self.time_data[-self.graph_points:]  # Keep only the last n data points
        self.rate_data = self.rate_data[-self.graph_points:]

        self.line.set_data(self.time_data, self.rate_data)
        self.thresh_line.set_ydata([self.rate_threshold / 1000, self.rate_threshold / 1000])
        if y_top is not None and y_top > 0:
            self.ax.set_ylim(0, y_top)
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()

        rate_alert_mesg, run_time_alert_mesg, junk_run_mesg = "Low Rate!", "Target Run Time Reached", "Junk Run"
        if junk:
            self.status_label.config(text=junk_run_mesg, foreground='gray', font=('Helvetica', 12, 'italic'))
        elif rate_alert:
            self.status_label.config(text=rate_alert_mesg, foreground='red', font=('Helvetica', 14, 'bold'))
        elif run_time_alert:
            self.status_label.config(text=run_time_alert_mesg, foreground='green', font=('Helvetica', 12, 'italic'))
        else:  # If status_label text is either of the alert messages, change it back to ""
            if self.status_label.cget('text') in [rate_alert_mesg, run_time_alert_mesg, junk_run_mesg]:
                self.status_label.config(text="", foreground='black')

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
This application monitors the DAQ rate from the Prometheus database via a Grafana proxy API call. It polls the database every 'check_time' seconds and retrieves the current run number and DAQ rate, averaged over the past 'integration_time' seconds. If the rate falls below the specified threshold, an alarm will sound. This is particularly helpful for quickly alerting the shift crew to seb hangs as well as beam aborts.

"""
        readme_text_widget.insert(tk.END, readme_text)

        # Add bold and bullet text
        parameters = [
            "Rate Threshold (Hz): An audible alarm will sound if the rate falls below this value.",
            "Integration Time (s): The time period over which the rate is averaged. Increase to reduce false alarms.",
            "Check Time (s): The interval between each database poll.",
            "Target Run Time (min): The targeted max time for each run. Only used if 'Run Time Reminder' is enabled.",
            "Alarm Points Cushion: The number of consecutive low rate reads required before sounding the alarm.",
            "New Run Cushion (s): The time to wait after a new run starts before alerting on low rate.",
            "Graph Points: The number of points to display on the rate plot.",
            "Run Time Reminder: Option to alert when the target run time is reached to remind the user to start a new run."
        ]

        readme_text_widget.insert(tk.END, "Parameters:\n", 'bold')
        for item in parameters:
            readme_text_widget.insert(tk.END, f"  • {item}\n", 'bullet')

        readme_text_widget.insert(tk.END, "\nButtons:\n", 'bold')
        buttons = [
            "Set: Apply the input parameters.",
            "Save Config: Save the current configuration to a file. These values will be loaded on next start of the GUI.",
            "Silence/Unsilence: Mute or unmute the alarm.",
            "Run Time Reminder: Alert when the target run time is reached.",
            "Readme: Display this readme."
        ]
        for item in buttons:
            readme_text_widget.insert(tk.END, f"  • {item}\n", 'bullet')

        readme_text_widget.insert(tk.END, "\nStatus and Plot:\n", 'bold')
        status_parameters = [
            "Last Check: Displays the timestamp of the last time the database was polled. Should be current time.",
            "Run Number: Shows the current run number.",
            "Run Time: Indicates the elapsed time for the current run. Only starts counting once the GUI has been opened.",
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

