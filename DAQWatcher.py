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
    def __init__(self, update_callback=None, rate_threshold=100, new_run_cushion=30, integration_time=10, check_time=1,
                 target_run_time=60, rate_alarm_cushion=2, alert_sound_file='prompt.wav', run_end_sound_file='xylofon.wav',
                 grafana_url='http://localhost:7815', database_uid='EflW1u9nz'):
        self.update_callback = update_callback
        self.rate_threshold = rate_threshold
        self.new_run_cushion = new_run_cushion
        self._integration_time = integration_time
        self.check_time = check_time
        self.rate_alarm_cushion = rate_alarm_cushion
        self.grafana_url = grafana_url
        self.database_uid = database_uid
        self.run_params = {'query': 'sphenix_rcdaq_run{hostname=~"gl1daq"}', 'instant': 'true'}
        self.daq_file_params = {
            'query': 'max by(run, filename, hostname) (sphenix_rcdaq_file_size_Byte{hostname=\"gl1daq\"})',
            'instant': 'false'}
        self.rate_params = self.get_rate_params()
        self.endpoint_url = f'{self.grafana_url}/api/datasources/proxy/uid/{self.database_uid}/api/v1/query'
        self.last_run = None
        self.run_start = None
        self.run_time = None

        self.repo_dir = os.path.dirname(os.path.abspath(__file__))
        self.alert_sound_file = os.path.join(self.repo_dir, alert_sound_file)
        self.run_end_sound_file = os.path.join(self.repo_dir, run_end_sound_file)

        self.silence = False
        self.target_run_time = target_run_time  # minutes Targeted run time, alert when reached
        self.run_time_reminder = None

        self.run_num = None
        self.rate = None
        self.latest_daq_file_name = None

    def get_rate_params(self):  # Unclear which query is best, seem to give same results
        query = f'rate(sphenix_gtm_gl1_register{{register="23"}}[{self.integration_time}s])'
        # query = f'rate(sphenix_gtm_gl1_json_dump_l1count{{}}[{self.integration_time}s])'
        # query = (f'rate(sphenix_gtm_gl1_json_dump_l1count{{}}[{self.integration_time}s])/'
        #          f'on() group_left() rate(sphenix_gtm_gl1_bco[{self.integration_time}s])*9.3831e6')
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

    def get_latest_daq_file_name(self):
        data = self.fetch_data(self.daq_file_params)
        if data and 'data' in data and 'result' in data['data']:
            result = data['data']['result']
            if len(result) > 0:
                return result[0]['metric']['filename']
        else:
            print(f'Error fetching DAQ file data: {data}')
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
        run_time_alert_counter, low_rate_counter = 0, 0
        while True:
            self.run_num = self.get_run_number()
            self.rate = self.get_rate()
            self.latest_daq_file_name = self.get_latest_daq_file_name()
            junk = 'junk' in self.latest_daq_file_name.lower() if self.latest_daq_file_name is not None else False

            rate_alert, run_time_alert = False, False

            # print(f'Run: {self.run_num}, Rate: {self.rate}, Silence: {self.silence}, run_time: {self.run_time}, '
            #       f'run_time_alert_counter: {run_time_alert_counter}')

            if self.rate is None or self.rate >= self.rate_threshold:
                low_rate_counter = 0

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
                        rate_alert = True
                        low_rate_counter += 1
                        if not self.silence and not junk and low_rate_counter >= self.rate_alarm_cushion:
                            os.system(f'aplay {self.alert_sound_file}')

                if self.target_run_time is not None and self.run_time > self.target_run_time * 60:
                    print('Target run time reached')
                    run_time_alert = True
                    if not self.silence and run_time_alert_counter < 5 and not junk:
                        os.system(f'aplay {self.run_end_sound_file}')
                        run_time_alert_counter += 1

            # Update the GUI with the latest data
            if self.update_callback:
                self.update_callback(self.run_num, self.rate, self.run_time, rate_alert, run_time_alert, junk)
            sleep(self.check_time)  # Do this first so continues are safe

    @property
    def integration_time(self):
        return self._integration_time

    @integration_time.setter
    def integration_time(self, value):
        self._integration_time = int(value)
        self.rate_params = self.get_rate_params()
