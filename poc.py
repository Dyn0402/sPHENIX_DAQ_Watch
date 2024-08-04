#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on August 02 09:24 2024
Created in PyCharm
Created as sPHENIX_DAQ_Watch/poc

@author: Dylan Neff, dn277127
"""

import os
import requests
from time import sleep, time


def main():
    # watch_daq()
    # print_exp_overview_dash()
    query_server_test()
    # query_mvtx_server_test()
    print('donzo')


def watch_daq():
    rate_threshold = 100
    new_run_cushion = 10  # seconds to wait after a new run starts before alerting on low rate
    alert_sound_file = '/usr/share/sounds/sound-icons/prompt.wav'
    grafana_url = 'http://localhost:7815'
    database_uid = 'EflW1u9nz'

    run_params = {'query': 'sphenix_rcdaq_run{hostname=~"gl1daq"}', 'instant': 'true'}
    endpoint_url = f'{grafana_url}/api/datasources/proxy/uid/{database_uid}/api/v1/query'
    response = requests.get(endpoint_url, params=run_params)
    print(response)
    print(response.json())

    rate_params = {'query': 'rate(sphenix_gtm_gl1_register{register="23"}[10s])', 'instant': 'true'}
    endpoint_url = f'{grafana_url}/api/datasources/proxy/uid/{database_uid}/api/v1/query'
    response = requests.get(endpoint_url, params=rate_params)
    print(response)
    print(response.json())

    last_run, run_start = None, None
    while True:
        try:
            response = requests.get(endpoint_url, params=run_params)
            run_num = response.json()['data']['result']
            if len(run_num) != 1:
                run_num = None
            else:
                run_num = int(run_num[0]['value'][-1])
        except Exception as e:
            print(f'Error getting run number: {e}')
            print(response.json())
            run_num = None

        try:
            response = requests.get(endpoint_url, params=rate_params)
            rate = float(response.json()['data']['result'][0]['value'][-1])
        except Exception as e:
            print(f'Error getting rate: {e}')
            print(response.json())
            rate = None

        print(f'Run: {run_num}, Rate: {rate}')

        if run_num != last_run:
            last_run = run_num
            run_start = time()
            print(f'New run: {run_num}')

        if rate is not None and run_num is not None:
            if rate < rate_threshold and time() - run_start > new_run_cushion:
                print('Low rate')
                os.system(f'aplay {alert_sound_file}')

        sleep(1)


def print_exp_overview_dash():
    url = 'http://localhost:7815/api/dashboards/uid/W4ivbg-Ik'
    res = requests.get(url).json()
    print(res['dashboard']['panels'][0])
    print(len(res['dashboard']['panels']))
    print(res['dashboard']['panels'][0].keys())
    print(res['dashboard']['panels'][0]['datasource'])
    for panel in res['dashboard']['panels']:
        if 'title' in panel:
            print(panel['title'])
        if 'datasource' in panel:
            print(panel['datasource'])
        if 'targets' in panel:
            print(panel['targets'])
        print()


def query_server_test():
    grafana_url = 'http://localhost:7815'
    database_uid = 'EflW1u9nz'

    # run_params = {'query': 'max by(run, filename, hostname) (sphenix_rcdaq_file_size_Byte{hostname=\"gl1daq\"})',
    #               'instant': 'false'}
    # run_params = {'query': 'sphenix_rcdaq_file_size_Byte{hostname=~\"ebdc23\"}',
    #               'instant': 'true'}
    # run_params = {'query': 'rate(sphenix_gtm_gl1_register{register="23"}[10s])', 'instant': 'false'}
    # run_params = {'query': 'rate(sphenix_gtm_gl1_trigger_scalar{type=\"scaled\"}[10s])', 'instant': 'false'}
    # run_params = {'query': 'rate(sphenix_gtm_gl1_bco[10s])', 'instant': 'false'}
    # run_params = {'query': 'rate(sphenix_gtm_gl1_json_dump_l1count{}[10s])/on() group_left() rate(sphenix_gtm_gl1_bco[10s])*9.3831e6', 'instant': 'false'}
    # run_params = {'query': 'rate(sphenix_gtm_gl1_json_dump_l1count{}[10s])', 'instant': 'false'}
    run_params = {'query': 'sphenix_gtm_gl1_json_dump_l1count{}[60s]', 'instant': 'false'}
    endpoint_url = f'{grafana_url}/api/datasources/proxy/uid/{database_uid}/api/v1/query'
    response = requests.get(endpoint_url, params=run_params)
    print(response)
    print(response.json())
    vals = response.json()['data']['result'][0]['values']
    print(vals)
    last_val = vals[-1]
    first_val = vals[0]
    print(f'Time diff: {last_val[0] - first_val[0]}, event diff: {int(last_val[1]) - int(first_val[1])}')


def query_mvtx_server_test():
    grafana_url = 'http://localhost:7815'
    database_uid = 'iQo4u_fVk'

    # SQL query extracted from the JSON
    sql_query = '''
    SELECT Value 
    FROM mvtx.mvtxStatus 
    ORDER BY Zeit DESC 
    LIMIT 1
    '''

    run_params = {
        'rawSql': sql_query,
    }

    endpoint_url = f'{grafana_url}/api/datasources/proxy/uid/{database_uid}/api/v1/query'

    try:
        response = requests.get(endpoint_url, params=run_params)
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
        print(response)
        print(response.json())
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")


def poc_testing():
    # url = 'http://localhost:7815/d/W4ivbg-Ik/experiment-overview?orgId=1&refresh=5s'
    url = 'http://localhost:7815/api/dashboards/uid/W4ivbg-Ik'
    # url = 'https://google.com'
    # url = ('https://ttp.cbp.dhs.gov/schedulerapi/locations/'
    #        '?temporary=true&inviteOnly=false&operational=true&serviceName=Global%20Entry')
    res = requests.get(url).json()
    # print(res)
    # print(res.keys())
    # print(len(res))
    # print(res['dashboard'].keys())
    # print(res['meta'].keys())
    print(res['dashboard']['panels'][0])
    print(len(res['dashboard']['panels']))
    print(res['dashboard']['panels'][0].keys())
    print(res['dashboard']['panels'][0]['datasource'])
    # print(res['GL1 Trigger'])
    url_datasource = 'http://localhost:7815/api/v1/query/EflW1u9nz'
    # headers = {
    #     'Authorization': f'Bearer {api_key}',
    #     'Content-Type': 'application/json'
    # }
    api_url = 'http://localhost:7815'
    dashboard_uid = 'W4ivbg-Ik'
    api_key = 'your_api_key'

    dashboard_data = fetch_grafana_dashboard(api_url, dashboard_uid, api_key)
    panel_title = 'Latest GL1 Run'
    panel_id, panel_query = get_panel_query(dashboard_data, panel_title)
    data_source_id = get_panel_data_source_id(dashboard_data, panel_title)

    print(panel_id)
    print(panel_query)
    print(data_source_id)
    prom_req = 'sphenix_rcdaq_run{hostname=~"gl1daq"}'
    print(requests.get(f'{api_url}/api/datasources/proxy/uid/{data_source_id}/{prom_req}'))
    #
    # prom_url = 'http://db1.sphenix.bnl.gov:9090'
    # prom_url = 'http://localhost:9090/'
    # print(requests.get(prom_url))
    # query_prometheus(prom_url, prom_req)
    # current_value = query_grafana(api_url, data_source_id, panel_query, api_key)
    # print(f'Current Value: {current_value}')
    # response = requests.get(query_url, headers=headers, params=params)
    # res_datasource = requests.get(url_datasource).json()
    # print(res_datasource)


def find_element_recursive(data, key_to_find):
    if isinstance(data, dict):
        for key, value in data.items():
            if key == key_to_find:
                return value
            result = find_element_recursive(value, key_to_find)
            if result is not None:
                return result
    elif isinstance(data, list):
        for item in data:
            result = find_element_recursive(item, key_to_find)
            if result is not None:
                return result
    return None


def fetch_grafana_dashboard(api_url, dashboard_uid, api_key):
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    response = requests.get(f'{api_url}/api/dashboards/uid/{dashboard_uid}', headers=headers)

    if response.status_code == 200:
        dashboard_data = response.json()
        return dashboard_data
    else:
        response.raise_for_status()


def get_panel_data_source_id(dashboard_data, panel_title):
    for panel in dashboard_data['dashboard']['panels']:
        if panel['title'] == panel_title:
            return panel['datasource']['uid']
    return None


def get_panel_query(dashboard_data, panel_title):
    for panel in dashboard_data['dashboard']['panels']:
        if panel['title'] == panel_title:
            return panel['id'], panel['targets'][0]['expr']  # Assuming the first target contains the query
    return None, None


def query_grafana(api_url, data_source_id, query, api_key):
    headers = {
        # 'Authorization': f'Bearer {api_key}',
        'Authorization': '',
        'Content-Type': 'application/json'
    }

    query_url = f'{api_url}/api/datasources/proxy/{data_source_id}/api/v1/query'
    params = {'query': query}

    response = requests.get(query_url, headers=headers, params=params)

    if response.status_code == 200:
        result = response.json()['data']['result']
        if result:
            return result[0]['value'][1]  # Return the current value
    else:
        response.raise_for_status()

    return None


def query_prometheus(prometheus_url, query):
    query_url = f'{prometheus_url}/api/v1/query'
    params = {'query': query}

    response = requests.get(query_url, params=params)

    if response.status_code == 200:
        result = response.json()['data']['result']
        if result:
            return result[0]['value'][1]  # Return the current value
    else:
        response.raise_for_status()

    return None


if __name__ == '__main__':
    main()

