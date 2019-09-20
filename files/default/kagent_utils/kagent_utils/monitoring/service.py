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

import os
import logging
import subprocess
import time

from threading import RLock
from datetime import datetime

from kagent_utils import http


class Service:
    INIT_STATE = "INIT"
    STARTED_STATE = "Started"
    STOPPED_STATE = "Stopped"

    def __init__(self, group, name, stdout_file, config_file, fail_attempts, kconfig, http):
        self.group = group
        self.name = name
        self.stdout_file = stdout_file
        self.config_file = config_file
        self.fail_attempts = fail_attempts
        self._host_id = kconfig.host_id
        self.http = http
        self.LOG = logging.getLogger(__name__)
        self._last_known_state = Service.INIT_STATE
        self.state_lock = RLock()
        self._num_of_failures = 0

    def get_state(self):
        try:
            self.state_lock.acquire()
            return self._last_known_state
        finally:
            self.state_lock.release()

    def set_state(self, state):
        try:
            self.state_lock.acquire()
            self._last_known_state = state
        finally:
            self.state_lock.release()

    def alive(self, currently=False):
        try:
            self.LOG.debug("Checking status of %s", self.name)
            command = ['systemctl', 'is-active', '--quiet', self.name]
            self._exec_check_call(command, stderr=subprocess.STDOUT)
            msg = "Service {0} is alive".format(self.name)
            if currently:
                self.LOG.info(msg)
            else:
                self.LOG.debug(msg)
            self._num_of_failures = 0
            return True
        except subprocess.CalledProcessError as e:
            if currently:
                self.LOG.error("Service %s is DEAD.", self.name)
                return False
            self._num_of_failures = self._num_of_failures + 1
            self.LOG.debug("Service %s has failed %i times",
                           self.name, self._num_of_failures)
            if self._num_of_failures >= self.fail_attempts:
                self.LOG.error("Service %s is DEAD.", self.name)
                return False
            return True

    def start(self):
        try:
            self.LOG.debug("Starting service: %s", self.name)
            command = ['sudo', 'systemctl', 'start', self.name]
            self._exec_check_output(command, stderr=subprocess.STDOUT)
            self.started()
            self.LOG.info("Started service: %s", self.name)
            return True
        except subprocess.CalledProcessError as e:
            self.LOG.error("Could not start service %s Exit code: %i Reason: %s",
                           self.name, e.returncode, e.output)
            return False

    def stop(self):
        try:
            self.LOG.debug("Stopping service: %s", self.name)
            command = ['sudo', 'systemctl', 'stop', self.name]
            self._exec_check_output(command, stderr=subprocess.STDOUT)
            self.failed()
            self.LOG.info("Stopped service: %s", self.name)
            return True
        except subprocess.CalledProcessError as e:
            self.LOG.error("Could not stop service %s Exit code: %i Reason: %s",
                           self.name, e.returncode, e.output)
            return False

    def restart(self):
        try:
            self.LOG.debug("Restarting service %s", self.name)
            command = ['sudo', 'systemctl', 'restart', self.name]
            self._exec_check_output(command, stderr=subprocess.STDOUT)
            self.started()
            self.LOG.info("Restarted service: %s", self.name)
            return True
        except:
            self.LOG.error("Could not restart service %s Exit code: %i Reason: %s",
                           self.name, e.returncode, e.output)
            return False

    def started(self):
        self.set_state(Service.STARTED_STATE)

    def failed(self):
        self.set_state(Service.STOPPED_STATE)

    def _exec_check_call(self, command, stdout=None, stderr=None):
        subprocess.check_call(command, stdout=stdout, stderr=stderr)

    def _exec_check_output(self, command, stderr=None):
        subprocess.check_output(command, stderr=stderr)

    def __str__(self):
        return "Service: {0}/{1} - State: {2}".format(self.group, self.name, self.get_state())
