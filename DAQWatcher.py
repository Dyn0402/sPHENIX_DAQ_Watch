#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on August 02 08:40 2024
Created in PyCharm
Created as sPHENIX_DAQ_Watch/DAQWatcher

@author: Dylan Neff, dn277127
"""

import os
import requests
from time import sleep, time


class DAQWatcher:
    def __init__(self, update_callback=None, rate_threshold=100, new_run_cushion=10, integration_time=10, check_time=1,
                 target_run_time=60, alert_sound_file='prompt.wav', run_end_sound_file='xylofon.wav',
                 grafana_url='http://localhost:7815', database_uid='EflW1u9nz'):
        self.update_callback = update_callback
        self.rate_threshold = rate_threshold
        self.new_run_cushion = new_run_cushion
        self._integration_time = integration_time
        self.check_time = check_time
        self.alert_sound_file = alert_sound_file
        self.run_end_sound_file = run_end_sound_file
        self.grafana_url = grafana_url
        self.database_uid = database_uid
        self.run_params = {'query': 'sphenix_rcdaq_run{hostname=~"gl1daq"}', 'instant': 'true'}
        self.rate_params = self.get_rate_params()
        self.endpoint_url = f'{self.grafana_url}/api/datasources/proxy/uid/{self.database_uid}/api/v1/query'
        self.last_run = None
        self.run_start = None
        self.run_time = None

        self.silence = False
        self.target_run_time = target_run_time  # minutes Targeted run time, alert when reached
        self.run_time_reminder = None

        self.run_num = None
        self.rate = None

    def get_rate_params(self):
        query = f'rate(sphenix_gtm_gl1_register{{register="23"}}[{self.integration_time}s])'
        return {'query': query, 'instant': 'true'}

    def fetch_data(self, params):
        try:
            response = requests.get(self.endpoint_url, params=params)
            return response.json()
        except Exception as e:
            print(f'Error fetching data: {e}')
            return None

    def get_run_number(self):
        data = self.fetch_data(self.run_params)
        if data and 'data' in data and 'result' in data['data']:
            result = data['data']['result']
            if len(result) == 1:
                return int(result[0]['value'][-1])
        return None

    def get_rate(self):
        data = self.fetch_data(self.rate_params)
        if data and 'data' in data and 'result' in data['data']:
            result = data['data']['result']
            if len(result) > 0:
                return float(result[0]['value'][-1])
            else:
                print(f'Error fetching rate data: {data}')
        else:
            print(f'Error fetching rate data: {data}')
        return None

    def watch_daq(self):
        run_time_alert_counter = 0
        while True:
            self.run_num = self.get_run_number()
            self.rate = self.get_rate()

            print(f'Run: {self.run_num}, Rate: {self.rate}, Silence: {self.silence}, run_time: {self.run_time}, '
                  f'run_time_alert_counter: {run_time_alert_counter}')

            if self.run_num is not None:
                if self.run_num != self.last_run:
                    self.last_run = self.run_num
                    self.run_start = time()
                    run_time_alert_counter = 0
                    print(f'New run: {self.run_num}')

                if self.run_start is None:
                    self.run_time = None
                else:
                    self.run_time = time() - self.run_start

                if self.rate is not None and self.run_num is not None:
                    if self.rate < self.rate_threshold and self.run_time > self.new_run_cushion:
                        print('Low rate')
                        if not self.silence:
                            os.system(f'aplay {self.alert_sound_file}')

                if self.target_run_time is not None and self.run_time > self.target_run_time * 60:
                    print('Target run time reached')
                    if not self.silence and run_time_alert_counter < 5:
                        os.system(f'aplay {self.run_end_sound_file}')
                        run_time_alert_counter += 1

            # Update the GUI with the latest data
            if self.update_callback:
                self.update_callback(self.run_num, self.rate, self.run_time)
            sleep(self.check_time)  # Do this first so continues are safe

    @property
    def integration_time(self):
        return self._integration_time

    @integration_time.setter
    def integration_time(self, value):
        self._integration_time = int(value)
        self.rate_params = self.get_rate_params()
