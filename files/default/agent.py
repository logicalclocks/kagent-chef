#!/usr/bin/env python

'''
Install:
 requests:    easy_install requests
 bottle:      easy_install bottle
 Cherrypy:    easy_install cherrypy
 pyOpenSSL:   apt-get install python-openssl
'''

import time
from datetime import datetime
import multiprocessing
from threading import Lock
import threading
import queue
import subprocess
from subprocess import Popen
from subprocess import CalledProcessError
import os
import sys
import configparser
import requests
import logging.handlers
import coloredlogs
import json
from bottle import Bottle, run, get, post, request, HTTPResponse, server_names, ServerAdapter, response
from cheroot import wsgi
from cheroot.ssl.builtin import BuiltinSSLAdapter
import ssl
import re
import argparse
import getpass

import kagent_utils
from kagent_utils import KConfig
from kagent_utils import IntervalParser

global mysql_process
mysql_process = None
var="~#@#@!#@!#!@#@!#"

config_mutex = Lock()

HTTP_OK = 200
AGENT_LOG_FILENAME = "agent.log"

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
    log_format = "%(asctime)s %(levelname)s [%(module)s/%(funcName)s] %(message)s"
    logger_formatter = logging.Formatter(log_format)

    coloredlogs.install(level=kconfig.logging_level, fmt=log_format)
    
    logger_file_handler = logging.handlers.RotatingFileHandler(agent_log_file, "w", maxBytes=kconfig.max_log_size, backupCount=1)
    logger_file_handler.setFormatter(logger_formatter)
    logger.addHandler(logger_file_handler)
    logger.setLevel(kconfig.logging_level)

    # Setup kagent_utils logger
    kagent_utils_logger = logging.getLogger('kagent_utils')
    kagent_utils_logger.setLevel(kconfig.logging_level)
    kagent_utils_logger.addHandler(logger_file_handler)
    
    # Setup csr logger
    csr_logger = logging.getLogger('csr')
    csr_logger.setLevel(kconfig.logging_level)
    csr_logger.addHandler(logger_file_handler)
    
    logger.info("Hops-Kagent started.")
    logger.info("Heartbeat URL: {0}".format(kconfig.heartbeat_url))
    logger.info("Host Id: {0}".format(kconfig.host_id))
    logger.info("Hostname: {0}".format(kconfig.hostname))
    logger.info("Public IP: {0}".format(kconfig.public_ip))
    logger.info("Private IP: {0}".format(kconfig.private_ip))
    
## Antonis: This should go away in the future!!! Used only by RESTCommandHandler execute
# reading services
def readServicesFile():
    try:
        global services
        services = configparser.ConfigParser()
        services.read(kconfig.services_file)

    except Exception as e:
        print("Error in the services file. Check its formatting: {0}: {1}".format(kconfig.services_file, e))
        logger.error("Exception while reading {0} file: {1}".format(kconfig.services_file, e))
        sys.exit(1)


logged_in = False

class Heartbeat():
    daemon_threads = True
    def __init__(self, commands_queue, system_commands_status, system_commands_status_mutex, host_services):
        self._commands_queue = commands_queue
        self._system_commands_status = system_commands_status
        self._system_commands_status_mutex = system_commands_status_mutex
        self._host_services = host_services
        self._recover = True
            
        while True:
            self.send()
            time.sleep(kconfig.heartbeat_interval)


    @staticmethod
    def login():
        global logged_in
        global session
        global master_token 
        try:
            session = requests.Session()
            resp = session.post(kconfig.login_url, data={'email': kconfig.server_username, 'password': kconfig.server_password}, verify=False)
            if not resp.status_code == HTTP_OK:
                logged_in = False
                logger.warn('Could not login agent to Hopsworks (Status code: {0}).'.format(resp.status_code))
            else:
                logger.info('Successful login of agent to Hopsworks (Status code: {0}).'.format(resp.status_code))
                logged_in = True
                master_token = resp.headers['Authorization'].split()[1]
        except Exception as err:
            logger.warn('Could not login agent to Hopsworks {0}'.format(err))
            logged_in = False
        return master_token

    def construct_services_status(self):
        services = []
        for name, service in self._host_services.items():
            srv_status = {}
            srv_status['group'] = service.group
            srv_status['service'] = service.name
            srv_status['status'] = service.get_state()
            services.append(srv_status)
        return services
    
    def send(self):
        global logged_in
        global session
        global master_token 
        if not logged_in:
           logger.info('Logging in to Hopsworks....')
           master_token = Heartbeat.login()
        else:
            system_status_to_delete = []
            try:
                logger.debug("Creating heartbeat reply...")
                services_list = self.construct_services_status()
                now = int(time.mktime(datetime.now().timetuple()))
                headers = {'content-type': 'application/json'}
                headers['Authorization'] = "Bearer " + master_token
                payload = {}
                payload["num-gpus"] = 0
                payload["host-id"] = kconfig.host_id
                payload["agent-time"] = now
                payload["services"] = services_list
                payload["recover"] = self._recover

                self._system_commands_status_mutex.acquire()
                system_commands_response = []
                # Append command status to response
                for k, v in self._system_commands_status.items():
                    system_commands_response.append(v)
                    system_status_to_delete.append(v)

                # Remove status from local statuses state
                for command_to_delete in system_status_to_delete:
                    del self._system_commands_status[command_to_delete['id']]
                self._system_commands_status_mutex.release()
                payload["system-commands"] = system_commands_response

                if (kconfig.private_ip != None):
                    payload["private-ip"] = kconfig.private_ip
                else:
                    payload["private-ip"] = ""

                payload["cores"] = cores
                logger.debug("Sending heartbeat...")
                resp = session.post(kconfig.heartbeat_url, data=json.dumps(payload), headers=headers, verify=False)
                logger.debug("Received heartbeat response")
                if not resp.status_code == HTTP_OK:
                    # Put back deleted statuses if command ID does not exist in order to be re-send
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

                    except Exception as err:
                        logger.info("No commands to execute")

            except Exception as err:
                logger.error("{0}. Retrying in {1} seconds...".format(err, kconfig.heartbeat_interval))
                logged_in = False


class Cloud():
    daemon_threads = True
    def __init__(self):

        while True:
            self.monitor()
            time.sleep(kconfig.cloud_monitor_interval)

    @staticmethod
    def isPreemtedAzure():
        headers = {'Metadata': 'true'}
        try:
            resp = requests.request("GET", kconfig.cloud_monitor_url, timeout=10, headers=headers)
            events = json.loads(resp.content)['Events']
            for event in events:
                if event['EventType'] == "Preempt":
                    return True    
        except Exception as err:
            logger.warn('Could not get events from the cloud {0}'.format(err))
        return False
    
    token = ""

    @staticmethod
    def getAWSToken():
        headers = {'X-aws-ec2-metadata-token-ttl-seconds': '21600'}
        resp = requests.request("PUT", "{0}/api/token".format(kconfig.cloud_monitor_url) , timeout=10, headers=headers)
        Cloud.token = resp.content

    @staticmethod
    def isPreemtedAWS():
        try:
            if Cloud.token == "":
                Cloud.getAWSToken()
            headers = {'X-aws-ec2-metadata-token': Cloud.token}
            resp = requests.request("GET", "{0}/meta-data/spot/instance-action".format(kconfig.cloud_monitor_url) , timeout=10, headers=headers)
            if resp.status_code == 401:
                Cloud.getAWSToken()
            elif resp.status_code == 200:
                return True
        except Exception as err:
            logger.warn('Could not get events from the cloud {0}'.format(err))
        return False

    def monitor(self):
        preempted = False
        if(kconfig.cloud_provider.lower()=="azure"):
            preempted = Cloud.isPreemtedAzure()
        if(kconfig.cloud_provider.lower()=="aws"):
            preempted = Cloud.isPreemtedAWS()
        if preempted:
            # call back to hopsworks-cloud to signal preemption
            headers = {"x-api-key": kconfig.api_key}
            url = "{gateway}/eventsv2/ops/users/{uid}/instances/{instance_id}/preempted"
            url = url.format(gateway=kconfig.gateway, uid=kconfig.uid, instance_id=kconfig.instance_id)

            data = {
                "nodeId": kconfig.node_id
            }
            try:
                requests.request("POST", url, json=data, timeout=10, headers=headers)
            except Exception as err:
                logger.warn('Could not send events to hopsworks-cloud {0}'.format(err))



class SystemCommandsHandler:
    def __init__(self, system_commands_status, system_commands_status_mutex, config_file_path):
        self._system_commands_status = system_commands_status
        self._system_commands_status_mutex = system_commands_status_mutex
        self._config_file_path = config_file_path

    def handle(self, command):
        if command is None:
            return
        logger.debug("Handling System command: {0}".format(command))
        op = command['op']

        if op == 'CONDA_GC':
            self._conda_gc(command)
        else:
            logger.error("Unknown OP {0} for system command {1}".format(op, command))

    def _conda_gc(self, command):
        try:
            logger.debug("Calling conda gc script")
            conda_gc_helper_script = os.path.join(kconfig.sbin_dir, "dockerImageDelete.sh")
            docker_image = command['arguments']

            logger.info("Deleting docker image {0}".format(docker_image))
            subprocess.check_call(["sudo", conda_gc_helper_script, "delete", docker_image])
            logger.info("Deleted docker image {0}".format(docker_image))

            command['status'] = 'FINISHED'
            logger.info("Successfully removed docker image")
        except CalledProcessError as e:
            logger.error("Error while deleting docker image: <{0}> Reason: {1}".format(docker_image, e))
            command['status'] = 'FAILED'
        except Exception as e:
            logger.error("General error while removing docker image {0}".format(e))
            command['status'] = 'FAILED'

        self._system_commands_status_mutex.acquire()
        logger.debug("Adding status {0} for command ID {1} - {2}".format(command['status'], command['id'], command))
        self._system_commands_status[command['id']] = command
        self._system_commands_status_mutex.release()


class Command:
    def __init__(self, command_type, command):
        self._command_type = command_type
        self._command = command
        if 'priority' in command:
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
    def __init__(self, commands_queue, systemCommandsHandler, group=None, target=None, name=None, args=(),
                 kwargs=None, verbose=None):
        threading.Thread.__init__(self, group=group, target=target, name=name)
        self.args = args
        self.kwargs = kwargs
        self._commands_queue = commands_queue
        self._systemCommandsHandler = systemCommandsHandler
        return

    def run(self):
        logger.info("Starting commands handling thread")
        while (True):
            c = self._commands_queue.get(block=True)
            logger.debug("Handling command {0}".format(c.get_command()))
            command_type = c.get_command_type()
            command = c.get_command()

            try:
                if (command_type == 'SYSTEM_COMMAND'):
                    logger.info("System command")
                    self._systemCommandsHandler.handle(command)
            except Exception as e:
                logger.error(">>> Error while handling command {0} - Error: {1}".format(c.get_command(), e))


## Antonis: Used only in RESTCommandHandler execute method. It should be
## *removed* along with the method!
class Config():

    def section_name(self, group, service=None):
        if service == None:
            return "{0}".format(group)
        else:
            return "{0}-{1}".format(group, service)

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

    def start(self, group, service):
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
            
    def stop(self, group, service):
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

            
    def restart(self, group, service):
        if not service in self._host_services:
            return self.error_response(400, "Service not installed.")
        else:
            srv = self._host_services[service]
            if srv.restart():
                return "Service started."
            else:
                return self.error_response(400, "Error: Cannot restart the service.")

            
    def read_log(self, group, service, lines):
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
    
    def read_config(self, group, service):
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

    def info(self, group, service):
        try:
            if service is None:
                section_name = "{0}".format(group)
            else:
                section_name = "{0}-{1}".format(group, service)

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
    def execute(self, group, service, command, params):
        try:
            if service == None:
                section = Config().section_name(group)
            else:
                section = Config().section_name(group, service)
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
        Heartbeat.send(False)
        return "OK"

HOME_DIR_PATTERN = re.compile('.*(\${HOME}).*')
USER_DIR_PATTERN = re.compile('.*(\${USER}).*')
def get_x509_material():
    cryptoDir = kconfig.crypto_dir
    user = getpass.getuser()
    if HOME_DIR_PATTERN.match(cryptoDir):
        home = os.path.expanduser('~')
        cryptoDir = re.sub("\${HOME}", home, cryptoDir)
    if USER_DIR_PATTERN.match(cryptoDir):
        cryptoDir = re.sub("\${USER}", user, cryptoDir)
    certificate = os.path.join(cryptoDir, user + "_pub.pem")
    private = os.path.join(cryptoDir, user + "_priv.pem")
    return certificate, private

class SSLCherryPy(ServerAdapter):
    def run(self, handler):
        server = wsgi.Server((self.host, self.port), handler)
        certificate, key = get_x509_material()
        ssl_adapter = BuiltinSSLAdapter(certificate, key)
        ssl_adapter.context.options |= ssl.OP_NO_SSLv2
        ssl_adapter.context.options |= ssl.OP_NO_SSLv3
        ssl_adapter.context.options |= ssl.OP_NO_TLSv1
        ssl_adapter.context.options |= ssl.OP_NO_TLSv1_1
        server.ssl_adapter = ssl_adapter
        try:
            server.start()
        finally:
            server.stop()

def construct_services(k_config, hw_http_client):
    host_services = {}
    for c_service in services.sections():
        group = services.get(c_service, 'group')
        if services.has_option(c_service, 'service'):
            service_name = services.get(c_service, 'service')
            if services.has_option(c_service, 'fail-attempts'):
                fail_attempts = services.getint(c_service, 'fail-attempts')
            else:
                fail_attempts = 1
            stdout_file = services.get(c_service, "stdout-file")
            config_file = services.get(c_service, "config-file")
            k_service = kagent_utils.Service(group, service_name, stdout_file,
                                             config_file, fail_attempts, k_config, hw_http_client)
            host_services[service_name] = k_service
    return host_services

# Maintain order of services from services file
def construct_ordered_services_list(k_config, hw_http_client):
    host_services = []
    for c_service in services.sections():
        group = services.get(c_service, 'group')
        if services.has_option(c_service, 'service'):
            service_name = services.get(c_service, 'service')
            if services.has_option(c_service, 'fail-attempts'):
                fail_attempts = services.getint(c_service, 'fail-attempts')
            else:
                fail_attempts = 1
            stdout_file = services.get(c_service, "stdout-file")
            config_file = services.get(c_service, "config-file")
            k_service = kagent_utils.Service(group, service_name, stdout_file,
                                             config_file, fail_attempts, k_config, hw_http_client)
            host_services.append(k_service)
    return host_services


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Hops nodes administration agent')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-c', '--config', default='config.ini', help='Path to configuration file')
    parser.add_argument('-s', '--services', choices=('start', 'stop', 'status'), help="Start/stop/status all local services and exit")

    args = parser.parse_args()
    
    verbose = args.verbose

    global kconfig
    kconfig = KConfig(args.config)
    kconfig.load()
    kconfig.read_conf()

    create_log_dir_if_not(kconfig)
    setupLogging(kconfig)
    readServicesFile()
        
    hw_http_client = kagent_utils.Http(kconfig)

    if args.services:
        ordered_host_services = construct_ordered_services_list(kconfig, hw_http_client)
        if args.services == 'start':
            for service in ordered_host_services:
                if not service.start():
                    service.start()
        elif args.services == 'stop':
            for service in reversed(ordered_host_services):
                if not service.stop():
                    service.stop()
        elif args.services == 'status':
            for service in ordered_host_services:
                service.alive(currently=True)
        sys.exit(-1)

    host_services = construct_services(kconfig, hw_http_client)

    agent_pid = str(os.getpid())
    with open(kconfig.agent_pidfile, 'w') as f:
        f.write(agent_pid)
    logger.info("Hops Kagent PID: {0}".format(agent_pid))
    
    interval_parser = IntervalParser()

    ## Start thread to monitor status of local services
    host_services_watcher_interval = interval_parser.get_interval_in_s(kconfig.watch_interval)
    host_services_monitor_action = kagent_utils.HostServicesWatcherAction(host_services)
    host_services_monitor = kagent_utils.Watcher(host_services_monitor_action, max(1, host_services_watcher_interval),
                                                 fail_after=sys.maxsize, name="host_services_monitor")
    host_services_monitor.setDaemon(True)
    host_services_monitor.start()
    
    commands_queue = queue.PriorityQueue(maxsize=100)
    system_commands_status = {}
    system_commands_status_mutex = Lock()
    config_file_path = os.path.abspath(args.config)
    system_commands_handler = SystemCommandsHandler(system_commands_status, system_commands_status_mutex,
                                                    config_file_path)

    ## Start commands handler thread
    commands_handler = Handler(commands_queue, system_commands_handler)
    commands_handler.setDaemon(True)
    commands_handler.start()

    ## Start heartbeat thread
    hb_thread = threading.Thread(target=Heartbeat, args=(commands_queue, system_commands_status, system_commands_status_mutex, host_services))
    hb_thread.setDaemon(True)
    hb_thread.start()

    ## Start cloud thread
    if hasattr(kconfig, 'monitor_cloud') and kconfig.monitor_cloud:
        cloud_thread = threading.Thread(target=Cloud, args=())
        cloud_thread.setDaemon(True)
        cloud_thread.start()


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
        
    @get('/restartService/<group>/<service>')
    def restartService(group, service):
        logger.info('Incoming REST Request:  GET /restartService/{0}/{1}'.format(group, service))
        if not _authenticate():
            return _authentication_error()

        if not service in host_services:
            return HTTPResponse(status=400, output='Group/Service not available.')

        return rest_command_handler.restart(group, service);

    @get('/startService/<group>/<service>')
    def startService(group, service):
        logger.info('Incoming REST Request:  GET /startService/{0}/{1}'.format(group, service))
        if not _authenticate():
            return _authentication_error()

        if not service in host_services:
            return HTTPResponse(status=400, output='Group/Service not available.')

        return rest_command_handler.start(group, service);

    @get('/stopService/<group>/<service>')
    def stopService(group, service):
        logger.info('Incoming REST Request:  GET /stopService/{0}/{1}'.format(group, service))
        if not _authenticate():
            return _authentication_error()

        if not service in host_services:
            return HTTPResponse(status=400, output='Group/Service not available.')

        return rest_command_handler.stop(group, service);

    @get('/config/<group>/<service>')
    def config(group, service):
        logger.info('Incoming REST Request:  GET /log/{0}/{1}'.format(group, service))
        if not _authenticate():
            return _authentication_error()

        if not service in host_services:
            return HTTPResponse(status=400, output='Group/Service not available.')

        return rest_command_handler.read_config(group, service);

    @get('/info/<group>/<service>')
    def info(group, service):
        logger.info('Incoming REST Request:  GET /status/{0}/{1}'.format(group, service))
        if not _authenticate():
            return _authentication_error()

        if not service in host_services:
            return HTTPResponse(status=400, output='Group/Service not available.')

        return rest_command_handler.info(group, service);

    @get('/refresh')  # request heartbeat
    def refresh():
        logger.info('Incoming REST Request:  GET /refresh')
        if not _authenticate():
            return _authentication_error()

        return rest_command_handler.refresh();

    @post('/execute/<state>/<group>/<service>/<command>')
    def execute_hdfs(state, group, service, command):
        logger.info('Incoming REST Request:  POST /execute/{0}/{1}/{2}/{3}'.format(state, group, service, command))
        if not _authenticate():
            return _authentication_error()
        
        if request.body.readlines():
            params =  request.body.readlines()[0]
        else:
            params = ""
        if state == "run" :
            if service == "-":
                return rest_command_handler.execute(group, None, command, params);
            else:
                return rest_command_handler.execute(group, service, command, params);
        return rest_command_handler.response(404, "Error")

    logger.info("RESTful service started.")
    run(host='0.0.0.0', port=kconfig.rest_port, server='sslcherrypy')
