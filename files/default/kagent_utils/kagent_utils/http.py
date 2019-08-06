# -*- coding: utf-8 -*-
# This file is part of Hopsworks
# Copyright (C) 2019, Logical Clocks AB. All rights reserved
 
# Hopsworks is free software: you can redistribute it and/or modify it under the terms of
# the GNU Affero General Public License as published by the Free Software Foundation,
# either version 3 of the License, or (at your option) any later version.

# Hopsworks is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License along with this program.
# If not, see <https://www.gnu.org/licenses/>.

import logging
import requests
import json

from threading import RLock
from requests import exceptions as requests_exceptions

class Http:
    JSON_HEADER = {'User-Agent': 'Agent', 'content-type': 'application/json'}
    FORM_HEADER = {'User-Agent': 'Agent', 'content-type': 'application/x-www-form-urlencoded'}
    HTTPS_VERIFY = False
    
    def __init__(self, k_config):
        self.k_config = k_config
        self.logged_in = False
        self.session = None
        self.LOG = logging.getLogger(__name__)
        self.lock = RLock()

    def _login(self):
        try :
            self.lock.acquire()
            if not self.logged_in or self.session is None:
                try :
                    self.session = requests.Session()
                    response = self.session.post(self.k_config.login_url, data={'email': self.k_config.server_username,
                                                                                'password': self.k_config.server_password},
                                                 headers=Http.FORM_HEADER, verify=Http.HTTPS_VERIFY)
                    response.raise_for_status()
                    self.logged_in = True
                    self.LOG.debug("Logged in to Hopsworks!")
                except requests_exceptions.RequestException as ex:
                    self.session = None
                    self.LOG.error("Could not login to Hopsworks! Error code: %i Reason: %s",
                                   response.status_code, response.reason)
                    raise ex
        finally:
            self.lock.release()
                    
