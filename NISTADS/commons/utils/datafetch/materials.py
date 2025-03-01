import numpy as np
import pandas as pd
import requests as r
import asyncio

from NISTADS.commons.utils.datafetch.status import GetServerStatus
from NISTADS.commons.utils.datafetch.asynchronous import data_from_multiple_URLs
from NISTADS.commons.constants import CONFIG
from NISTADS.commons.logger import logger


# [CHECK SERVER STATUS]
###############################################################################
server = GetServerStatus()
server.check_status()


# [NIST DATABASE API: GUEST/HOST]
###############################################################################
class GuestHostDataFetch: 

    def __init__(self, configuration):      
        self.url_GUEST = 'https://adsorption.nist.gov/isodb/api/gases.json'
        self.url_HOST = 'https://adsorption.nist.gov/matdb/api/materials.json'
        self.guest_fraction = configuration["collection"]["GUEST_FRACTION"]
        self.host_fraction = configuration["collection"]["HOST_FRACTION"]        
        self.max_parallel_calls = configuration["collection"]["PARALLEL_TASKS"]
        self.guest_identifier = 'InChIKey'
        self.host_identifier = 'hashkey'

    # function to retrieve HTML data
    #--------------------------------------------------------------------------
    def get_guest_host_index(self):
        
        '''
        Retrieves adsorbates and adsorbents data from specified URLs. This function sends GET 
        requests to the URLs specified in the instance variables `self.url_adsorbents` and `self.url_adsorbates`. 
        It then checks the status of the response and if successful (status code 200), 
        it converts the JSON response to a Python dictionary. If the request fails, 
        it prints an error message and sets the corresponding index to None.

        Returns:            
            tuple: A tuple containing two elements:
                - adsorbates_index (dict or None): A dictionary containing the adsorbates data if the request was successful, None otherwise.
                - adsorbents_index (dict or None): A dictionary containing the adsorbents data if the request was successful, None otherwise.
        
        ''' 
        guest_json = r.get(self.url_GUEST)
        host_json = r.get(self.url_HOST)

        if guest_json.status_code == 200:
            guest_index = guest_json.json() 
            guest = pd.DataFrame(guest_index)
            logger.info(f'Total number of adsorbents: {guest.shape[0]}')
        else:
            logger.error(f'Failed to retrieve adsorbents data. Status code: {guest_json.status_code}')       
            guest = None
        if host_json.status_code == 200:
            host_index = host_json.json() 
            host = pd.DataFrame(host_index) 
            logger.info(f'Total number of adsorbates: {host.shape[0]}')
        else:
            logger.error(f'Failed to retrieve adsorbates data. Status code: {host_json.status_code}')
            host = None
  
        return guest, host     

    # function to retrieve HTML data
    #--------------------------------------------------------------------------
    def get_guest_host_data(self, guest=None, host=None):        
        loop = asyncio.get_event_loop()
        guest_data = None
        if guest is not None and isinstance(guest, pd.DataFrame):
            guest_samples = int(np.ceil(self.guest_fraction * guest.shape[0]))
            guest_names = guest[self.guest_identifier].to_list()[:guest_samples]
            guest_urls = [f'https://adsorption.nist.gov/isodb/api/gas/{name}.json' for name in guest_names]
            guest_data = loop.run_until_complete(data_from_multiple_URLs(guest_urls, self.max_parallel_calls))
            guest_data = [data for data in guest_data if data is not None]
            guest = pd.DataFrame(guest_data) 
        else:
            logger.error('No available guest data has been found. Skipping directly to host species')
            
        if host is not None and isinstance(host, pd.DataFrame):  
            host_samples = int(np.ceil(self.host_fraction * host.shape[0]))
            host_names = host[self.host_identifier].to_list()[:host_samples]       
            host_urls = [f'https://adsorption.nist.gov/isodb/api/material/{name}.json' for name in host_names]       
            host_data = loop.run_until_complete(data_from_multiple_URLs(host_urls, self.max_parallel_calls))        
            host_data = [data for data in host_data if data is not None] 
            host = pd.DataFrame(host_data)            
        else:
            logger.error('No available host data has been found.')        
            
        return guest, host 

      


