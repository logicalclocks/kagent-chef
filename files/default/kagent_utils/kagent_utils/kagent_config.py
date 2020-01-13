import sys
import ConfigParser
import logging
import random
import string
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
            self.register_url = self.server_url + \
                self._config.get('server', 'path-register')
            self.ca_host_url = self.server_url + \
                self._config.get('server', 'path-ca-host')
            self.login_url = self.server_url + \
                self._config.get('server', 'path-login')
            self.heartbeat_url = self.server_url + \
                self._config.get('server', 'path-heartbeat')
            self.server_username = self._config.get('server', 'username')
            self.server_password = self._config.get('server', 'password')
            self.rest_port = self._config.getint('agent', 'restport')
            self.heartbeat_interval = self._config.getfloat(
                'agent', 'heartbeat-interval')
            self.logging_level_str = self._config.get('agent', 'logging-level')
            self.logging_level = self._get_logging_level(
                self.logging_level_str)
            self.agent_log_dir = self._config.get('agent', 'agent-log-dir')
            self.csr_log_file = self._config.get('agent', 'csr-log-file')
            self.max_log_size = self._config.getint('agent', 'max-log-size')
            self.agent_pidfile = self._config.get('agent', 'pid-file')
            self.certificate_file = self._config.get(
                'agent', 'certificate-file')
            self.key_file = self._config.get('agent', 'key-file')
            self.server_keystore = self._config.get('agent', 'server-keystore')
            self.server_truststore = self._config.get(
                'agent', 'server-truststore')
            self.keystore_script = self._config.get('agent', 'keystore-script')
            self.services_file = self._config.get('agent', 'services-file')
            self.watch_interval = self._config.get('agent', 'watch-interval')
            self.bin_dir = self._config.get('agent', 'bin-dir')
            self.sbin_dir = self._config.get('agent', 'sbin-dir')
            self.group_name = self._config.get('agent', 'group-name')
            self.hadoop_home = self._config.get('agent', 'hadoop-home')
            self.certs_dir = self._config.get('agent', 'certs-dir')
            self.certs_user = self._config.get('agent', 'certs-user')
            self.state_store_location = self._config.get(
                'agent', 'state-store')
            self.agent_password = self._config.get('agent', 'password')
            self.conda_dir = self._config.get('agent', 'conda-dir')
            self.conda_user = self._config.get('agent', 'conda-user')
            self.conda_envs_blacklist = self._config.get(
                'agent', 'conda-envs-blacklist')
            self.conda_gc_interval = self._config.get(
                'agent', 'conda-gc-interval')
            self.public_ip = self._config.get('agent', 'public-ip')
            self.private_ip = self._config.get('agent', 'private-ip')

            if (self._config.has_option("agent", "hostname")):
                self.hostname = self._config.get("agent", "hostname")
            else:
                try:
                    self.hostname = socket.gethostbyaddr(self.private_ip)[0]
                except socket.herror:
                    try:
                        self.hostname = socket.getfqdn()
                    except socket.herror:
                        self.hostname = "localhost"

            if (self._config.has_option("agent", "host-id")):
                self.host_id = self._config.get("agent", "host-id")
            else:
                self.host_id = self.hostname

            self.elk_key_file = self._config.get('agent', 'elk-key-file')
            self.elk_certificate_file = self._config.get('agent', 'elk-certificate-file')
            self.elk_cn = self._config.get('agent', 'elk-cn')
            self.elastic_host_certificate = self._config.get('agent', 'elastic-host-certificate')
            self.hops_ca_cert_file = self._config.get('agent', 'hops_ca-cert-file')
        except Exception, e:
            print("Exception while reading {0}: {1}".format(
                self._configFile, e))
            sys.exit(1)

    def _get_logging_level(self, log_level_str):
        return self._log_level_mapping.get(log_level_str.upper(), logging.INFO)
