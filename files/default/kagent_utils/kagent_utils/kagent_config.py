import sys
import ConfigParser
import logging
import random
import string
import netifaces
import socket

from IPy import IP

class KConfig:
    """Class representig kagent configuration"""

    _log_level_mapping = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL}
    
    def __init__(self, configFile):
        self._configFile = configFile

    def set_conf_value(self, section, name, value):
        """Set a new configuration property"""
        if self._config is not None:
            self._config.set(section, name, value)

    def dump_to_file(self):
        """Dump configuration object to file"""
        with open(self._configFile, 'wb') as fd:
            self._config.write(fd)
            
    def read_conf(self):
        """Load configuration from file"""
        try:
            self._config = ConfigParser.ConfigParser()
            self._config.read(self._configFile)
            self.server_url = self._config.get('server', 'url')
            self.register_url = self.server_url + self._config.get('server', 'path-register')
            self.ca_host_url = self.server_url + self._config.get('server', 'path-ca-host')
            self.login_url = self.server_url + self._config.get('server', 'path-login')
            self.heartbeat_url = self.server_url + self._config.get('server', 'path-heartbeat')
            self.alert_url = self.server_url + self._config.get('server', 'path-alert')
            self.server_username = self._config.get('server', 'username')
            self.server_password = self._config.get('server', 'password')
            self.rest_port = self._config.getint('agent', 'restport')
            self.heartbeat_interval = self._config.getfloat('agent', 'heartbeat-interval')
            self.logging_level_str = self._config.get('agent', 'logging-level')
            self.logging_level = self._get_logging_level(self.logging_level_str)
            self.agent_log_file = self._config.get('agent', 'agent-log-file')
            self.csr_log_file = self._config.get('agent', 'csr-log-file')
            self.max_log_size = self._config.getint('agent', 'max-log-size')
            self.agent_pidfile = self._config.get('agent', 'pid-file')
            self.network_interface = self._config.get('agent', 'network-interface')
            self.certificate_file = self._config.get('agent', 'certificate-file')
            self.ca_file = self._config.get('agent', 'ca-file')
            self.key_file = self._config.get('agent', 'key-file')
            self.server_keystore = self._config.get('agent', 'server-keystore')
            self.server_truststore = self._config.get('agent', 'server-truststore')
            self.keystore_script = self._config.get('agent', 'keystore-script')
            self.services_file = self._config.get('agent', 'services-file')
            self.watch_interval = self._config.getfloat('agent', 'watch-interval')
            self.bin_dir = self._config.get('agent', 'bin-dir')
            self.mysql_socket = self._config.get('agent', 'mysql-socket')
            self.group_name = self._config.get('agent', 'group-name')
            self.hadoop_home = self._config.get('agent', 'hadoop-home')
            self.certs_dir = self._config.get('agent', 'certs-dir')
            self.state_store_location = self._config.get('agent', 'state-store')
            self.agent_password = self._config.get('agent', 'password')
            self.conda_dir = self._config.get('agent', 'conda-dir')
            self.conda_python_versions = self._config.get('agent', 'conda-python-versions')
            self.conda_gc_interval = self._config.get('agent', 'conda-gc-interval')

            # TODO find public/private IP addresses
            self.public_ip = None
            self.private_ip = None
            self.eth0_ip = netifaces.ifaddresses(self.network_interface)[netifaces.AF_INET][0]['addr']
            if (IP(self.eth0_ip).iptype() == "PUBLIC"):
                self.public_ip = self.eth0_ip
            else:
                self.private_ip = self.eth0_ip

            if (self._config.has_option("agent", "hostname")):
                self.hostname = self._config.get("agent", "hostname")
            else:
                try:
                    self.hostname = socket.gethostbyaddr(self.eth0_ip)[0]
                except socket.herror:
                    try:
                        self.hostname = socket.gethostname()
                    except socket.herror:
                        self.hostname = "localhost"

            if (self._config.has_option("agent", "host-id")):
                self.host_id = self._config.get("agent", "host-id")
            else:
                self.host_id = self.hostname
        except Exception, e:
            print ("Exception while reading {0}: {1}".format(self._configFile, e))
            sys.exit(1)

    def _get_logging_level(self, log_level_str):
        return self._log_level_mapping.get(log_level_str.upper(), logging.INFO)
