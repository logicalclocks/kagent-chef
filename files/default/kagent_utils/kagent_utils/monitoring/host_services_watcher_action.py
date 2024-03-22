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

from kagent_utils import watcher_action
from .service import Service

class HostServicesWatcherAction(watcher_action.WatcherAction):
    def __init__(self, host_services):
        self.host_services = host_services
        self.LOG = logging.getLogger(__name__)
        
    def preAction(self, *args, **kwargs):
        pass

    def action(self, *args, **kwargs):
        for name, service in self.host_services.items():
            self.LOG.debug("Polling status for %s", name)

            if service.alive():
                if service.get_state() == Service.STOPPED_STATE or service.get_state() == Service.INIT_STATE:
                    self.LOG.info("Service %s started", service)
                    service.started()
            else:
                if service.get_state() == Service.STARTED_STATE or service.get_state() == Service.INIT_STATE:
                    service.failed()
                
    def postAction(self, *args, **kwargs):
        pass
