#!/usr/bin/env python

'''
Install:
 requests:    easy_install requests
 bottle:      easy_install bottle
 Cherrypy:    easy_install cherrypy
 Netifaces:   easy_install netifaces
 IPy:         easy_install ipy
 pyOpenSSL:   apt-get install python-openssl
'''

import time
from time import sleep
from datetime import datetime
import multiprocessing
import thread
from threading import Lock
import threading
import Queue
import subprocess
from subprocess import Popen
from subprocess import CalledProcessError
import os
import sys
import ConfigParser
import requests
import logging.handlers
import json
from OpenSSL import crypto
import socket
from os.path import exists, join
from bottle import Bottle, run, get, post, request, HTTPResponse, server_names, ServerAdapter, response
from cheroot import wsgi
from cheroot.ssl.builtin import BuiltinSSLAdapter
import netifaces
from IPy import IP
import re
from collections import defaultdict
import io
import tempfile
import argparse
from hops import devices

import kagent_utils
from kagent_utils import KConfig
from kagent_utils import IntervalParser
from kagent_utils import UnrecognizedIntervalException

global mysql_process
mysql_process = None
var="~#@#@!#@!#!@#@!#"

config_mutex = Lock()
conda_mutex = Lock()

HTTP_OK = 200
AGENT_LOG_FILENAME = "agent.log"

global conda_ongoing
conda_ongoing = defaultdict(lambda: False)

cores = multiprocessing.cpu_count()

def create_log_dir_if_not(kconfig):
    log_dir = kconfig.agent_log_dir
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
        
# logging
def setupLogging(kconfig):
    agent_log_file = os.path.join(kconfig.agent_log_dir, AGENT_LOG_FILENAME)
    try:
        os.remove(agent_log_file + '.1')
    except:
        pass
    with open(agent_log_file, 'w'):  # clear log file
        pass
    
    global logger
    logger = logging.getLogger('agent')

    logger_formatter = logging.Formatter('%(asctime)s %(levelname)s [%(module)s/%(funcName)s] %(message)s')
    logger_file_handler = logging.handlers.RotatingFileHandler(agent_log_file, "w", maxBytes=kconfig.max_log_size, backupCount=1)
    logger_stream_handler = logging.StreamHandler()
    logger_file_handler.setFormatter(logger_formatter)
    logger_stream_handler.setFormatter(logger_formatter)
    logger.addHandler(logger_file_handler)
    logger.addHandler(logger_stream_handler)
    logger.setLevel(kconfig.logging_level)

    # Setup kagent_utils logger
    kagent_utils_logger = logging.getLogger('kagent_utils')
    kagent_utils_logger.setLevel(kconfig.logging_level)
    kagent_utils_logger.addHandler(logger_file_handler)
    kagent_utils_logger.addHandler(logger_stream_handler)

    # Setup csr logger
    csr_logger = logging.getLogger('csr')
    csr_logger.setLevel(kconfig.logging_level)
    csr_logger.addHandler(logger_file_handler)
    csr_logger.addHandler(logger_stream_handler)

    logger.info("Hops-Kagent started.")
    logger.info("Heartbeat URL: {0}".format(kconfig.heartbeat_url))
    logger.info("Alert URL: {0}".format(kconfig.alert_url))
    logger.info("Host Id: {0}".format(kconfig.host_id))
    logger.info("Hostname: {0}".format(kconfig.hostname))
    logger.info("Public IP: {0}".format(kconfig.public_ip))
    logger.info("Private IP: {0}".format(kconfig.private_ip))

def prepare_conda_commands_logger(kconfig):
    logger = logging.getLogger(CONDA_COMMANDS_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    file_handler = logging.handlers.RotatingFileHandler(os.path.join(kconfig.agent_log_dir, "conda_commands.log"))
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
## Antonis: This should go away in the future!!! Used only by RESTCommandHandler execute
# reading services
def readServicesFile():
    try:
        global services
        services = ConfigParser.ConfigParser()
        services.read(kconfig.services_file)

    except Exception, e:
        print "Error in the services file. Check its formatting: {0}: {1}".format(kconfig.services_file, e)
        logger.error("Exception while reading {0} file: {1}".format(kconfig.services_file, e))
        sys.exit(1)


logged_in = False

class Heartbeat():
    daemon_threads = True
    def __init__(self, commands_queue, system_commands_status, system_commands_status_mutex,
                 conda_commands_status, conda_commands_status_mutex, conda_report_interval,
                 conda_envs_monitor_list, host_services):
        self._commands_queue = commands_queue
        self._system_commands_status = system_commands_status
        self._system_commands_status_mutex = system_commands_status_mutex
        self._conda_commands_status = conda_commands_status
        self._conda_commands_status_mutex = conda_commands_status_mutex
        self._conda_envs_monitor_list = conda_envs_monitor_list
        # in ms
        self._conda_report_interval = conda_report_interval
        self._last_conda_report = long(time.mktime(datetime.now().timetuple()) * 1000)
        self._host_services = host_services
        self._recover = True
            
        while True:
            self.send()
            time.sleep(kconfig.heartbeat_interval)


    @staticmethod
    def login():
        json_headers = {'User-Agent': 'Agent', 'content-type': 'application/json'}
        form_headers = {'User-Agent': 'Agent', 'content-type': 'application/x-www-form-urlencoded'}
        payload = {}
        global logged_in
        global session
        try:
            session = requests.Session()
            resp = session.post(kconfig.login_url, data={'email': kconfig.server_username, 'password': kconfig.server_password}, headers=form_headers, verify=False)
#            resp = session.put(kconfig.register_url, data=json.dumps(payload), headers=json_headers, verify=False)
            if not resp.status_code == HTTP_OK:
                logged_in = False
                logger.warn('Could not login agent to Hopsworks (Status code: {0}).'.format(resp.status_code))
            else:
                logger.info('Successful login of agent to Hopsworks (Status code: {0}).'.format(resp.status_code))
                logged_in = True
        except Exception as err:
            logger.warn('Could not login agent to Hopsworks {0}'.format(err))
            logged_in = False

    def is_conda_gc_triggered(self):
        conda_report = False
        CONDA_CONTROL = '/tmp/trigger_conda_gc'
        if os.path.isfile(CONDA_CONTROL):
            with open(CONDA_CONTROL, 'r') as fd:
                if int(next(fd)) == 1:
                    conda_report = True

            if conda_report:
                with open(CONDA_CONTROL, 'w') as fd:
                    fd.write('0')

        return conda_report

    def construct_services_status(self):
        services = []
        for name, service in self._host_services.iteritems():
            srv_status = {}
            srv_status['cluster'] = service.cluster
            srv_status['group'] = service.group
            srv_status['service'] = service.name
            # Antonis: Do we even need this?
            srv_status['web-port'] = 0
            srv_status['status'] = service.get_state()
            services.append(srv_status)
        return services
    
    def send(self):
        global logged_in
        global session
        if not logged_in:
           logger.info('Logging in to Hopsworks....')
           Heartbeat.login()
        else:
            system_status_to_delete = []
            conda_status_to_delete = []
            try:
                logger.debug("Creating heartbeat reply...")
                disk_info = DiskInfo()
                memory_info = MemoryInfo()
                load_info = LoadInfo()
                services_list = self.construct_services_status()
                now = long(time.mktime(datetime.now().timetuple()))
                headers = {'content-type': 'application/json'}
                payload = {}
                payload["num-gpus"] = devices.get_num_gpus()
                payload["host-id"] = kconfig.host_id
                payload["agent-time"] = now
                payload["load1"] = load_info.load1
                payload["load5"] = load_info.load5
                payload["load15"] = load_info.load15
                payload["disk-used"] = disk_info.used
                payload['memory-used'] = memory_info.used
                payload["services"] = services_list
                payload["recover"] = self._recover
                
                now_in_ms = now * 1000
                time_to_report = (now_in_ms - self._last_conda_report) > self._conda_report_interval
                if self.is_conda_gc_triggered() or time_to_report:
                    logger.debug("Triggering Conda GC")
                    envs_slice = self._conda_envs_monitor_list.slice(10)
                    if envs_slice is not None:
                        logger.debug("Investigating Anaconda envs for GC: {0}".format(envs_slice))
                        payload["conda-report"] = list(envs_slice)
                    else:
                        logger.debug("No Anaconda envs for GC")
                    self._last_conda_report = now_in_ms
                    
                commands_status = {}

                self._system_commands_status_mutex.acquire()
                system_commands_response = []
                # Append command status to response
                for k, v in self._system_commands_status.iteritems():
                    system_commands_response.append(v)
                    system_status_to_delete.append(v)

                # Remove status from local statuses state
                for command_to_delete in system_status_to_delete:
                    del self._system_commands_status[command_to_delete['id']]
                self._system_commands_status_mutex.release()
                payload["system-commands"] = system_commands_response

                self._conda_commands_status_mutex.acquire()
                conda_commands_response = []
                # Append command status to response
                for k, v in self._conda_commands_status.iteritems():
                    conda_commands_response.append(v)
                    conda_status_to_delete.append(v)

                # Remove status from local statuses state
                for command_to_delete in conda_status_to_delete:
                    del self._conda_commands_status[command_to_delete['id']]

                self._conda_commands_status_mutex.release()
                payload["conda-commands"] = conda_commands_response

                if (kconfig.private_ip != None):
                    payload["private-ip"] = kconfig.private_ip
                else:
                    payload["private-ip"] = ""

                payload["cores"] = cores
                payload["disk-capacity"] = disk_info.capacity
                payload['memory-capacity'] = memory_info.total
                logger.debug("Sending heartbeat...")
                resp = session.post(kconfig.heartbeat_url, data=json.dumps(payload), headers=headers, verify=False)
                logger.debug("Received heartbeat response")
                if not resp.status_code == HTTP_OK:
                    # Put back deleted statuses if command ID does not exist in order to be re-send
                    self._conda_commands_status_mutex.acquire()
                    for restore_command in conda_status_to_delete:
                        if restore_command['id'] not in self._conda_commands_status:
                            self._conda_commands_status[restore_command['id']] = restore_command
                    self._conda_commands_status_mutex.release()

                    self._system_commands_status_mutex.acquire()
                    for restore_command in system_status_to_delete:
                        if restore_command['id'] not in self._system_commands_status:
                            self._system_commands_status[restore_command['id']] = restore_command
                    self._system_commands_status_mutex.release()

                    logged_in = False
                    raise Exception('Heartbeat could not be sent (Status code: {0})'.format(resp.status_code))
                else:
                    theResponse = resp.json()
                    logger.debug("Response from heartbeat is: {0}".format(theResponse))
                    self._recover = False
                    try:
                        system_commands = theResponse['system-commands']
                        for command in system_commands:
                            c = Command('SYSTEM_COMMAND', command)
                            logger.debug("Adding SYSTEM command with ID {0} and status {1} to Handler Queue".format(command['id'], command['status']))
                            commands_queue.put(c)
                            command['status'] = 'ONGOING'
                            self._system_commands_status_mutex.acquire()
                            self._system_commands_status[command['id']] = command
                            self._system_commands_status_mutex.release()

                        conda_commands = theResponse['conda-commands']
                        for command in conda_commands:
                            c = Command('CONDA_COMMAND', command)
                            logger.debug("Adding CONDA command with ID {0} and status {1} to Handler Queue".format(command['id'], command['status']))
                            commands_queue.put(c)
                            command['status'] = 'ONGOING'
                            self._conda_commands_status_mutex.acquire()
                            self._conda_commands_status[command['id']] = command
                            self._conda_commands_status_mutex.release()
                    except Exception as err:
                        logger.info("No commands to execute")
                        for data in theResponse['condaCommands']:
                            proj = data['proj']
                            conda_ongoing[proj] = False

            except Exception as err:
                logger.error("{0}. Retrying in {1} seconds...".format(err, kconfig.heartbeat_interval))
                logged_in = False

CONDA_COMMAND_LOG_PATTERN = "{project_name} {operation} {artifact} {artifact_version} {exit_code} {return_message}"
CONDA_COMMANDS_LOGGER_NAME = __name__ + "/conda_commands"

class CondaCommandsHandler:
    def __init__(self, conda_commands_status, conda_commands_status_mutex):
        self._conda_commands_status = conda_commands_status
        self._conda_commands_status_mutex = conda_commands_status_mutex
        self._commands_logger = logging.getLogger(CONDA_COMMANDS_LOGGER_NAME)

    def handle(self, command):
        global conda_ongoing
        if (command is None):
            return
        logger.debug("Handling Conda command: {0}".format(json.dumps(command, indent=2)))
        op = command['op'].upper()
        user = command['user']
        proj = command['proj']
        command_id = command['id']
        offline = ""
        logger.info("Command to execute: {0}/{1}/{2}".format(op, proj, command_id))
        if (conda_ongoing[proj] == False):
            conda_ongoing[proj] = True
            logger.info("Executing Command {0}/{1}/{2}".format(user, op, proj))
            arg = ""
            if 'arg' in command:
                arg = command['arg']
            if op == "REMOVE" or op == "CLONE" or op == "CREATE" or op == "YML" or op == "CLEAN":
                self._envOp(command, arg, offline)
            elif op == "INSTALL" or op == "UNINSTALL" or op == "UPGRADE":  # Conda package  commands (install, uninstall, upgrade)
                self._libOp(command)
            else:
                logger.error("Unkown command OP: {0} Ignoring...".format(op))
        else:
            logger.warn("Conda busy executing a command for project: {0}".format(proj))


    def _log_conda_command(self, project_name, operation, artifact, artifact_version, exit_code, return_message):
        log = CONDA_COMMAND_LOG_PATTERN.format(project_name=project_name.strip().lower(),
                                               operation=operation.strip(),
                                               artifact=artifact.strip(),
                                               artifact_version=artifact_version,
                                               exit_code=exit_code,
                                               return_message=return_message.strip())
        self._commands_logger.info(log)
        
    def _envOp(self, command, arg, offline):
        global conda_ongoing
        if not arg:
            arg=""
        user = command['user']
        command_id = command['id']
        op = command['op'].upper()
        proj = command['proj']
        install_jupyter = str(command['installJupyter']).lower()

        tempfile_fd = None
        if command['op'] == 'YML':
            tempfile_fd = tempfile.NamedTemporaryFile(suffix='.yml', delete=True)
            arg = tempfile_fd.name
            tempfile_fd.write(command['environmentYml'])
            tempfile_fd.flush()
            os.chmod(tempfile_fd.name, 0604)

        script = kconfig.bin_dir + "/anaconda_env.sh"
        logger.info("sudo {0} {1} {2} {3} {4} '{5}' {6} {7}".format(script, user, op, proj, arg, offline, kconfig.hadoop_home, install_jupyter))
        msg=""
        try:
            self._log_conda_command(proj, op, proj, arg, -1, 'WORKING')
            msg = subprocess.check_output(['sudo', script, user, op, proj, arg, offline, kconfig.hadoop_home, install_jupyter], cwd=kconfig.conda_dir, stderr=subprocess.STDOUT)
            command['status'] = 'SUCCESS'
            command['arg'] = arg
            self._log_conda_command(proj, op, proj, arg, 0, 'SUCCESS')
        except subprocess.CalledProcessError as e:
            logger.warn("Exception in envOp {0}".format(e.output))
            logger.warn("Exception in envOp. Ret code: {0}".format(e.returncode))
            self._log_conda_command(proj, op, proj, arg, e.returncode, e.output)
            command['status'] = 'FAILED'
        finally:
            if command['op'] == 'YML' and tempfile_fd != None:
                tempfile_fd.close()
            if command_id != -1:
                self._conda_commands_status_mutex.acquire()
                logger.debug("Adding status {0} for command ID {1} - {2}".format(command['status'], command_id, command))
                self._conda_commands_status[command_id] = command
                self._conda_commands_status_mutex.release()
            conda_ongoing[proj] = False
        return msg

    def _libOp(self, command):
        global conda_ongoing
        user = command['user']
        command_id = command['id']
        op = command['op'].upper()
        proj = command['proj']
        version = command['version']
        channelUrl = command['channelUrl']
        installType = command['installType']
        lib = command['lib']
        if not channelUrl:
            channelUrl="default"
        if not version:
            version=""
        script = kconfig.bin_dir + "/conda.sh"

        try:
            command_str = "sudo {0} {1} {2} {3} {4} {5} {6} {7}".format(script, user, op, proj, channelUrl, installType, lib, version)
            logger.info("Executing libOp command {0}".format(command_str))
            self._log_conda_command(proj, op, lib, version, -1, 'WORKING')
            msg = subprocess.check_output(['sudo', script, user, op, proj, channelUrl, installType, lib, version], cwd=kconfig.conda_dir, stderr=subprocess.STDOUT)
            logger.info("Lib op finished without error.")
            logger.info("{0}".format(msg))
            command['status'] = 'SUCCESS'
            self._log_conda_command(proj, op, lib, version, 0, 'SUCCESS')
        except subprocess.CalledProcessError as e:
            logger.warn("Exception in libOp {0}".format(e.output))
            logger.warn("Exception in libOp. Ret code: {0}".format(e.returncode))
            self._log_conda_command(proj, op, lib, version, e.returncode, e.output)
            command['status'] = 'FAILED'
        finally:
            conda_ongoing[proj] = False
            if command_id != -1:
                self._conda_commands_status_mutex.acquire()
                logger.debug("Adding status {0} for command ID {1} - {2}".format(command['status'], command_id, command))
                self._conda_commands_status[command_id] = command
                self._conda_commands_status_mutex.release()


class SystemCommandsHandler:
    def __init__(self, system_commands_status, system_commands_status_mutex, config_file_path, conda_envs_monitor_list):
        self._system_commands_status = system_commands_status
        self._system_commands_status_mutex = system_commands_status_mutex
        self._config_file_path = config_file_path
        self._conda_envs_monitor_list = conda_envs_monitor_list

    def handle(self, command):
        if command is None:
            return
        logger.debug("Handling System command: {0}".format(command))
        op = command['op']

        if op == 'SERVICE_KEY_ROTATION':
            self._service_key_rotation(command)
        elif op == 'CONDA_GC':
            self._conda_env_garbage_collection(command)
        else:
            logger.error("Unknown OP {0} for system command {1}".format(op, command))

    def _conda_env_garbage_collection(self, command):
        to_be_removed = json.loads(command['arguments'])
        exec_user = command['execUser']

        conda_bin = os.path.join(kconfig.conda_dir, 'bin', 'conda')
        for env in to_be_removed:
            try:
                script = os.path.join(kconfig.bin_dir, 'anaconda_env.sh')
                subprocess.check_call(['sudo', script, exec_user, 'REMOVE', env, '', '', '', ''], cwd=kconfig.conda_dir)
                logger.info("Removed Anaconda environment {0}".format(env))
                self._conda_envs_monitor_list.remove(env)
            except CalledProcessError as e:
                logger.warn("Could not remove environment {0} - exit code {1}".format(env, e.returncode))
        command['status'] = 'FINISHED'
        try:
            self._system_commands_status_mutex.acquire()
            self._system_commands_status[command['id']] = command
        finally:
            self._system_commands_status_mutex.release()

    def _service_key_rotation(self, command):
        try:
            logger.debug("Calling certificate rotation script")
            csr_helper_script = os.path.join(kconfig.certs_dir, "run_csr.sh")
            subprocess.check_call(["sudo", csr_helper_script, self._config_file_path, "rotate"])
            
            command['status'] = 'FINISHED'
            logger.info("Successfully rotated service certificates")
        except CalledProcessError as e:
            logger.error("Error while calling csr script: {0}".format(e))
            command['status'] = 'FAILED'
        except Exception as e:
            logger.error("General error while rotating certificates {0}".format(e))
            command['status'] = 'FAILED'

        self._system_commands_status_mutex.acquire()
        logger.debug("Adding status {0} for command ID {1} - {2}".format(command['status'], command['id'], command))
        self._system_commands_status[command['id']] = command
        self._system_commands_status_mutex.release()


class Command:
    def __init__(self, command_type, command):
        self._command_type = command_type
        self._command = command
        if command.has_key('priority'):
            self._priority = command['priority']
        else:
            self._priority = 0

    def __cmp__(self, other):
        if self._priority < other._priority:
            return 1
        elif self._priority > other._priority:
            return -1
        else:
            if self._command['id'] < other._command['id']:
                return -1
            elif self._command['id'] > other._command['id']:
                return 1
            else:
                return 0

    def get_command_type(self):
        return self._command_type

    def get_command(self):
        return self._command

class Handler(threading.Thread):
    def __init__(self, commands_queue, systemCommandsHandler, condaCommandsHandler,
                 group=None, target=None, name=None, args=(), kwargs=None, verbose=None):
        threading.Thread.__init__(self, group=group, target=target, name=name, verbose=verbose)
        self.args = args
        self.kwargs = kwargs
        self._commands_queue = commands_queue
        self._systemCommandsHandler = systemCommandsHandler
        self._condaCommandsHandler = condaCommandsHandler
        return

    def run(self):
        logger.info("Starting commands handling thread")
        while (True):
            c = self._commands_queue.get(block=True)
            logger.debug("Handling command {0}".format(c.get_command()))
            command_type = c.get_command_type()
            command = c.get_command()

            try:
                if (command_type == 'CONDA_COMMAND'):
                    logger.info("Conda command")
                    self._condaCommandsHandler.handle(command)
                elif (command_type == 'SYSTEM_COMMAND'):
                    logger.info("System command")
                    self._systemCommandsHandler.handle(command)
            except Exception as e:
                logger.error(">>> Error while handling command {0} - Error: {1}".format(c.get_command(), e))


class MemoryInfo(object):
    def __init__(self):
        process = subprocess.Popen("free", shell=True, stdout=subprocess.PIPE)
        stdout_list = process.communicate()[0].split('\n')
        for line in stdout_list:
            data = line.split()
            try:
                if data[0] == "Mem:":
                    self.total = int(data[1]) * 1024
                    self.used = int(data[2]) * 1024
                    self.free = int(data[3]) * 1024
                    self.buffers = int(data[5]) * 1024
                    self.cached = int(data[6]) * 1024
                    break
            except IndexError:
                continue


class DiskInfo(object):
    def __init__(self):
        disk = os.statvfs("/")
        self.capacity = disk.f_bsize * disk.f_blocks
        self.used = disk.f_bsize * (disk.f_blocks - disk.f_bavail)


class LoadInfo(object):
    def __init__(self):
        self.load1 = os.getloadavg()[0]
        self.load5 = os.getloadavg()[1]
        self.load15 = os.getloadavg()[2]

## Antonis: Used only in RESTCommandHandler execute method. It should be
## *removed* along with the method!
class Config():

    def section_name(self, cluster, group, service=None):
        if service == None:
            return "{0}-{1}".format(cluster, group)
        else:
            return "{0}-{1}-{2}".format(cluster, group, service)

    def get_section(self, section):
        config_mutex.acquire()
        items = {}
        try:
            for key, val in services.items(section):
                items[key] = val
        finally:
            config_mutex.release()
        return items

    def get(self, section, option):
        config_mutex.acquire()
        val = ""
        try:
            val = services.get(section, option)
        finally:
            config_mutex.release()
        return val

class RESTCommandHandler():

    def __init__(self, host_services):
        self._host_services = host_services
        
    def error_response(self, code, msg):
        resp = HTTPResponse(status=code, body=msg)
        logger.warn("{0}".format(resp))
        return resp

    def start(self, cluster, group, service):
        if not service in self._host_services:
            return self.error_response(400, "Service not installed.")
        else:
            srv = self._host_services[service]
            if srv.get_state() == kagent_utils.Service.STARTED_STATE:
                return self.error_response(400, "Service already started.")

            if srv.start():
                return "Service started"
            else:
                return self.error_response(400, "Error: Cannot start the service.")
            
    def stop(self, cluster, group, service):
        if not service in self._host_services:
            return self.error_response(400, "Service not installed.")
        else:
            srv = self._host_services[service]
            current_srv_state = srv.get_state()
            if (current_srv_state == kagent_utils.Service.STOPPED_STATE or
                current_srv_state == kagent_utils.Service.INIT_STATE):
                return self.error_response(400, "Service is not running.")

            if srv.stop():
                return "Service stopped."
            else:
                return self.error_response(400, "Error: Cannot stop the service.")

            
    def restart(self, cluster, group, service):
        if not service in self._host_services:
            return self.error_response(400, "Service not installed.")
        else:
            srv = self._host_services[service]
            if srv.restart():
                return "Service started."
            else:
                return self.error_response(400, "Error: Cannot restart the service.")

            
    def read_log(self, cluster, group, service, lines):
        try:
            lines = int(lines)

            if service not in self._host_services:
                return self.error_response(400, "Service not installed.")
            srv = self._host_services[service]
            log = self._tail_logs(srv.stdout_file, lines)
            return log

        except Exception as err:
            logger.error(err)
            return self.error_response(400, "Cannot read file.")

    def read_agent_log(self, lines):
        try:
            agent_log_file = os.path.join(kconfig.agent_log_dir, AGENT_LOG_FILENAME)
            log = self._tail_logs(agent_log_file, lines)
            return log

        except Exception as err:
            logger.error(err)
            return self.error_response(400, "Cannot read file.")

    def _tail_logs(self, file_name, n):
        stdin, stdout = os.popen2("tail -n {0} {1}".format(n, file_name))
        stdin.close()
        lines = stdout.readlines();
        stdout.close()
        log = "".join(str(x) for x in lines)
        return log
    
    def read_config(self, cluster, group, service):
        try:
            if service not in self._host_services:
                return self.error_response(400, "Service not installed.")
            srv = self._host_services[service]
            with open(srv.config_file) as config_file:
                conf = "".join(str(x) for x in (list(config_file)))
            return conf

        except Exception as err:
            logger.error(err)
            return self.error_response(400, "Cannot read file.")

    def info(self, cluster, group, service):
        try:
            if service is None:
                section_name = "{0}-{1}".format(cluster, group)
            else:
                section_name = "{0}-{1}-{2}".format(cluster, group, service)

            items = {}
            for key, val in services.items(section):
                items[key] = val

            resp = json.dumps(items)
            return resp

        except Exception as err:
            logger.error(err)
            return self.error_response(400, "Cannot read file.")

    ## Antonis: Most probably we don't need this and it should be
    ## removed in the future
    def execute(self, cluster, group, service, command, params):
        try:
            if service == None:
                section = Config().section_name(cluster, group)
            else:
                section = Config().section_name(cluster, group, service)
            script = Config().get(section, "command-script")
            logger.info("Script name executing is: {0}".format(script))
            env = Config().get(section, "command-env")
            command = env + " " + script + " " + params
            command = re.sub(r'([\"])', r'\\\1', command)
            as_user = Config().get(section, "command-user")
# TODO: could check if as_user == "root" or as_user == "sudo" here...
            if not as_user:
                logger.warn("No user supplied to execute command: {0}".format(command))
                raise Exception("Not allowed execute command as user: {0}".format(as_user))
            if as_user:
                command = "su - " + as_user + " -c \"" + command + "\""
# TODO: shell=True is insecure when using untrusted input
# as an attacker can input "hdfs dfs -ls / ; rm -rf /"
            p = Popen(command , shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            out, err = p.communicate()
            return out
        except Exception as err:
            logger.error(err)
            return self.error_response(400, "Could not execute.")


    def refresh(self):
        Heartbeat.send(False);
        return "OK"


class SSLCherryPy(ServerAdapter):
    def run(self, handler):
        server = wsgi.Server((self.host, self.port), handler)
        server.ssl_adapter = BuiltinSSLAdapter(kconfig.certificate_file, kconfig.key_file)
        try:
            server.start()
        finally:
            server.stop()

def construct_services(k_config, hw_http_client):
    host_services = {}
    for c_service in services.sections():
        cluster = services.get(c_service, 'cluster')
        group = services.get(c_service, 'group')
        if services.has_option(c_service, 'service'):
            service_name = services.get(c_service, 'service')
            if services.has_option(c_service, 'fail-attempts'):
                fail_attempts = services.getint(c_service, 'fail-attempts')
            else:
                fail_attempts = 1
            stdout_file = services.get(c_service, "stdout-file")
            config_file = services.get(c_service, "config-file")
            k_service = kagent_utils.Service(cluster, group, service_name, stdout_file,
                                             config_file, fail_attempts, k_config, hw_http_client)
            host_services[service_name] = k_service
        else:
            logger.info("Not watching %s/%s/%s", cluster, group, service_name)
    return host_services
            

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Hops nodes administration agent')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-c', '--config', default='config.ini', help='Path to configuration file')

    args = parser.parse_args()
    
    verbose = args.verbose

    global kconfig
    kconfig = KConfig(args.config)
    kconfig.read_conf()

    create_log_dir_if_not(kconfig)
    setupLogging(kconfig)
    prepare_conda_commands_logger(kconfig)
    readServicesFile()
        
    hw_http_client = kagent_utils.Http(kconfig)

    host_services = construct_services(kconfig, hw_http_client)

    agent_pid = str(os.getpid())
    file(kconfig.agent_pidfile, 'w').write(agent_pid)
    logger.info("Hops Kagent PID: {0}".format(agent_pid))
    
    interval_parser = IntervalParser()

    ## Start thread to monitor status of local services
    host_services_watcher_interval = interval_parser.get_interval_in_s(kconfig.watch_interval)
    host_services_monitor_action = kagent_utils.HostServicesWatcherAction(host_services)
    host_services_monitor = kagent_utils.Watcher(host_services_monitor_action, max(1, host_services_watcher_interval),
                                                 fail_after=sys.maxint, name="host_services_monitor")
    host_services_monitor.setDaemon(True)
    host_services_monitor.start()

    ## Start thread to perform Anaconda environments garbage collection
    conda_report_interval = interval_parser.get_interval_in_ms(kconfig.conda_gc_interval)
    conda_envs_monitor_list = kagent_utils.ConcurrentCircularLinkedList()
    watcher_action = kagent_utils.CondaEnvsWatcherAction(conda_envs_monitor_list, kconfig)
    watcher_interval = int(interval_parser.get_interval_in_s(kconfig.conda_gc_interval) / 2)
    # Default interval to 1 second. We don't want the watcher to spin like crazy
    conda_envs_watcher = kagent_utils.Watcher(watcher_action, max(1, watcher_interval), name="conda_gc_watcher")
    conda_envs_watcher.setDaemon(True)
    conda_envs_watcher.start()

    
    commands_queue = Queue.PriorityQueue(maxsize=100)
    system_commands_status = {}
    system_commands_status_mutex = Lock()
    config_file_path = os.path.abspath(args.config)
    system_commands_handler = SystemCommandsHandler(system_commands_status, system_commands_status_mutex,
                                                    config_file_path, conda_envs_monitor_list)

    conda_commands_status = {}
    conda_commands_status_mutex = Lock()
    conda_commands_handler = CondaCommandsHandler(conda_commands_status, conda_commands_status_mutex)

    ## Start commands handler thread
    commands_handler = Handler(commands_queue, system_commands_handler, conda_commands_handler)
    commands_handler.setDaemon(True)
    commands_handler.start()

    ## Start heartbeat thread
    hb_thread = threading.Thread(target=Heartbeat, args=(commands_queue, system_commands_status, system_commands_status_mutex,
                                                         conda_commands_status, conda_commands_status_mutex, conda_report_interval,
                                                         conda_envs_monitor_list, host_services))
    hb_thread.setDaemon(True)
    hb_thread.start()




    # The REST code uses a CherryPy webserver, but Bottle for the REST endpoints
    # WSGI server for SSL
    # For a a tutorial on the REST code below, see http://bottlepy.org/docs/dev/tutorial.html

    rest_command_handler = RESTCommandHandler(host_services)

    server_names['sslcherrypy'] = SSLCherryPy
    app = Bottle()
    @get('/ping')
    def ping():
        logger.info('Incoming REST Request:  GET /ping')
        return "Hops-Agent: Pong"

    def _authenticate():
        try:
            password = request.params['password']
            if password == kconfig.agent_password:
                return True
            return False
        except Exception:
            logger.error("Authentication failed: Invalid password!")
            return False

    def _authentication_error():
        return HTTPResponse(status=400, output="Invalid password")
        
    @get('/restartService/<cluster>/<group>/<service>')
    def restartService(cluster, group, service):
        logger.info('Incoming REST Request:  GET /restartService/{0}/{1}/{2}'.format(cluster, group, service))
        if not _authenticate():
            return _authentication_error()

        if not service in host_services:
            return HTTPResponse(status=400, output='Cluster/Group/Service not available.')

        return rest_command_handler.restart(cluster, group, service);

    @get('/startService/<cluster>/<group>/<service>')
    def startService(cluster, group, service):
        logger.info('Incoming REST Request:  GET /startService/{0}/{1}/{2}'.format(cluster, group, service))
        if not _authenticate():
            return _authentication_error()

        if not service in host_services:
            return HTTPResponse(status=400, output='Cluster/Group/Service not available.')

        return rest_command_handler.start(cluster, group, service);

    @get('/stopService/<cluster>/<group>/<service>')
    def stopService(cluster, group, service):
        logger.info('Incoming REST Request:  GET /stopService/{0}/{1}/{2}'.format(cluster, group, service))
        if not _authenticate():
            return _authentication_error()

        if not service in host_services:
            return HTTPResponse(status=400, output='Cluster/Group/Service not available.')

        return rest_command_handler.stop(cluster, group, service);

    @get('/log/<cluster>/<group>/<service>/<lines>')
    def log(cluster, group, service, lines):
        logger.info('Incoming REST Request:  GET /log/{0}/{1}/{2}/{3}'.format(cluster, group, service, lines))
        if not _authenticate():
            return _authentication_error()

        if not service in host_services:
            return HTTPResponse(status=400, output='Cluster/Group/Service not available.')

        return rest_command_handler.read_log(cluster, group, service, lines);


    @get('/agentlog/<lines:int>')
    def agentlog(lines):
        logger.info('Incoming REST Request:  GET /agentlog/{0}'.format(lines))
        if not _authenticate():
            return _authentication_error()

        return rest_command_handler.read_agent_log(lines);

    @get('/config/<cluster>/<group>/<service>')
    def config(cluster, group, service):
        logger.info('Incoming REST Request:  GET /log/{0}/{1}/{2}'.format(cluster, group, service))
        if not _authenticate():
            return _authentication_error()

        if not service in host_services:
            return HTTPResponse(status=400, output='Cluster/Group/Service not available.')

        return rest_command_handler.read_config(cluster, group, service);

    @get('/info/<cluster>/<group>/<service>')
    def info(cluster, group, service):
        logger.info('Incoming REST Request:  GET /status/{0}/{1}/{2}'.format(cluster, group, service))
        if not _authenticate():
            return _authentication_error()

        if not service in host_services:
            return HTTPResponse(status=400, output='Cluster/Group/Service not available.')

        return rest_command_handler.info(cluster, group, service);

    @get('/refresh')  # request heartbeat
    def refresh():
        logger.info('Incoming REST Request:  GET /refresh')
        if not _authenticate():
            return _authentication_error()

        return rest_command_handler.refresh();

    @post('/execute/<state>/<cluster>/<group>/<service>/<command>')
    def execute_hdfs(state, cluster, group, service, command):
        logger.info('Incoming REST Request:  POST /execute/{0}/{1}/{2}/{3}/{4}'.format(state, cluster, group, service, command))
        if not _authenticate():
            return _authentication_error()
        
        if request.body.readlines():
            params =  request.body.readlines()[0]
        else:
            params = ""
        if state == "run" :
            if service == "-":
                return rest_command_handler.execute(cluster, group, None, command, params);
            else:
                return rest_command_handler.execute(cluster, group, service, command, params);
        return rest_command_handler.response(404, "Error")



    @get('/conda/<user>/<command_id>/<op>/<proj>/<lib>')
    def conda(user,command_id,op,proj,lib):
        logger.info('Incoming REST Request:  GET /conda/{0}/{1}/{2}'.format(op, proj, lib))
        if not _authenticate():
            return _authentication_error()

        channelurl = request.params['channelurl']
        version = request.params['version']
        try:
            msg = Conda().conda(user,command_id, op, proj, channelurl, lib, version)
            resp = HTTPResponse(status=HTTP_OK, output=msg)
            logger.info("{0}".format(resp))
            return resp
        except Exception as err:
            logger.error("{0}".format(err))
            return rest_command_handler.response(400, "Error")

    # Normal client sets 'channel' to 'defaults' for http://conda.anaconda.org/ or 'system' to get system packages
    # curl -k -X GET https://10.0.2.15:8090/create/project?password=blah
    # curl -k -X GET https://10.0.2.15:8090/clone/projectSrc/projectDest?password=blah
    @get('/anaconda/<user>/<command_id>/<op>/<proj>/<arg>')
    def anaconda(user, command_id, op, proj, arg):
        logger.info('Incoming REST Request:  GET /anaconda/{0}/{1}/{2}'.format(user, op, proj))
        if not _authenticate():
            return _authentication_error()

        # Blocking REST call here
        arg = "default"
        if (op == "clone"):
            arg = request.params['srcproj']
        try:
            msg = Conda()._envOp(user, command_id, op, proj, arg, "")
            resp = HTTPResponse(status=HTTP_OK, output=msg)
            logger.info("{0}".format(resp))
            return resp
        except Exception as err:
            logger.error("{0}".format(err))
            return rest_command_handler.response(400, "Error")

    logger.info("RESTful service started.")
    run(host='0.0.0.0', port=kconfig.rest_port, server='sslcherrypy')

