import unittest
import configparser
import os
import tempfile
import netifaces
import socket

from IPy import IP

from kagent_utils import KConfig

class TestKConfig(unittest.TestCase):

    ## server section
    url = 'http://localhost:1337/'
    path_login = 'login/path'
    path_register = 'register/path'
    path_ca_host = 'ca/host/path'
    path_heartbeat = 'heartbeat/path'
    path_alert = 'alert/path'
    username = 'username'
    server_password = 'server_password'

    ## agent section
    host_id = 'host_0'
    restport = '8080'
    heartbeat_interval = '3'
    services_file = 'path/to/services/file'
    watch_interval = '4'
    bin_dir = 'path/to/bin/dir'
    pid_file = 'path/to/pid/file'
    agent_log_dir = 'path/to/agent/logs'
    csr_log_file = 'path/to/csr/log_file'
    logging_level = 'DEBUG'
    max_log_size = '100'
    mysql_socket = 'path/to/mysql/socket'
    hostname = 'myhostname'
    network_interface = ''
    group_name = 'group'
    hadoop_home = 'path/to/hadoop_home'
    certs_dir = 'path/to/certs_dir'
    certificate_file = 'path/to/certificate'
    key_file = 'path/to/key'
    server_keystore = 'path/to/server_keystore'
    server_truststore = 'path/to/server_truststore'
    keystore_script = 'path/to/keystore_script'
    state_store = 'path/to/state_store'
    agent_password = 'agent_password'
    conda_dir = 'path/to/conda'
    conda_envs_blacklist = 'python27,python35,hops-system'
    conda_gc_interval = '2h'

    def setUp(self):
        self.config_file = tempfile.mkstemp(prefix='kagent_config_')


    def tearDown(self):
        os.remove(self.config_file[1])


    def test_parse_full_config(self):
        self._prepare_config_file(True)
        
        config = KConfig(self.config_file[1])
        config.read_conf()

        self.assertEqual(self.url, config.server_url)
        self.assertEqual(self._toUrl(self.path_login), config.login_url)
        self.assertEqual(self._toUrl(self.path_register), config.register_url)
        self.assertEqual(self._toUrl(self.path_ca_host), config.ca_host_url)
        self.assertEqual(self._toUrl(self.path_heartbeat), config.heartbeat_url)
        self.assertEqual(self._toUrl(self.path_alert), config.alert_url)
        self.assertEqual(self.username, config.server_username)
        self.assertEqual(self.server_password, config.server_password)
        self.assertEqual(self.host_id, config.host_id)
        self.assertEqual(int(self.restport), config.rest_port)
        self.assertEqual(int(self.heartbeat_interval), config.heartbeat_interval)
        self.assertEqual(self.services_file, config.services_file)
        self.assertEqual(int(self.watch_interval), config.watch_interval)
        self.assertEqual(self.bin_dir, config.bin_dir)
        self.assertEqual(self.pid_file, config.agent_pidfile)
        self.assertEqual(self.agent_log_dir, config.agent_log_dir)
        self.assertEqual(self.csr_log_file, config.csr_log_file)
        self.assertEqual(self.logging_level, config.logging_level_str)
        self.assertEqual(int(self.max_log_size), config.max_log_size)
        my_ip = netifaces.ifaddresses(self.network_interface)[netifaces.AF_INET][0]['addr']
        if (IP(my_ip).iptype() == "PUBLIC"):
            self.assertEqual(my_ip, config.public_ip)
        else:
            self.assertEqual(my_ip, config.private_ip)
        self.assertEqual(self.mysql_socket, config.mysql_socket)
        self.assertEqual(self.hostname, config.hostname)
        self.assertEqual(self.network_interface, config.network_interface)
        self.assertEqual(self.group_name, config.group_name)
        self.assertEqual(self.hadoop_home, config.hadoop_home)
        self.assertEqual(self.certs_dir, config.certs_dir)
        self.assertEqual(self.certificate_file, config.certificate_file)
        self.assertEqual(self.key_file, config.key_file)
        self.assertEqual(self.server_keystore, config.server_keystore)
        self.assertEqual(self.server_truststore, config.server_truststore)
        self.assertEqual(self.keystore_script, config.keystore_script)
        self.assertEqual(self.state_store, config.state_store_location)
        self.assertEqual(self.agent_password, config.agent_password)
        self.assertEqual(self.conda_dir, config.conda_dir)
        self.assertEqual(self.conda_envs_blacklist, config.conda_envs_blacklist)
        self.assertEqual(self.conda_gc_interval, config.conda_gc_interval)

    ## Let KConfig figure out values for these properties
    def test_parse_partial_config(self):
        self._prepare_config_file(False)
        config = KConfig(self.config_file[1])
        config.read_conf()

        self.assertIsNotNone(config.agent_password)
        self.assertNotEqual('', config.agent_password)
        
        my_ip = netifaces.ifaddresses(self.network_interface)[netifaces.AF_INET][0]['addr']
        my_hostname = socket.gethostbyaddr(my_ip)[0]
        self.assertEqual(my_hostname, config.hostname)

        self.assertEqual(my_hostname, config.host_id)
        

    def _get_interface_name(self):
        # We hope that there is at least lo and another configured interface
        return netifaces.interfaces()[1]

    def _prepare_config_file(self, all_keys):
        config = configparser.ConfigParser()
        self.network_interface = self._get_interface_name()
        
        config['server'] = {
            'url': self.url,
            'path-login': self.path_login,
            'path-register': self.path_register,
            'path-ca-host': self.path_ca_host,
            'path-heartbeat': self.path_heartbeat,
            'path-alert': self.path_alert,
            'username': self.username,
            'password': self.server_password
        }

        if all_keys:
            config['agent'] = {
                'host-id': self.host_id,
                'restport': self.restport,
                'heartbeat-interval': self.heartbeat_interval,
                'services-file': self.services_file,
                'watch-interval': self.watch_interval,
                'bin-dir': self.bin_dir,
                'pid-file': self.pid_file,
                'agent-log-dir': self.agent_log_dir,
                'csr-log-file': self.csr_log_file,
                'logging-level': self.logging_level,
                'max-log-size': self.max_log_size,
                'mysql-socket': self.mysql_socket,
                'hostname': self.hostname,
                'network-interface': self.network_interface,
                'group-name': self.group_name,
                'hadoop-home': self.hadoop_home,
                'certs-dir': self.certs_dir,
                'certificate-file': self.certificate_file,
                'key-file': self.key_file,
                'server-keystore': self.server_keystore,
                'server-truststore': self.server_truststore,
                'keystore-script': self.keystore_script,
                'state-store': self.state_store,
                'password': self.agent_password,
                'conda-dir': self.conda_dir,
                'conda-envs-blacklist': self.conda_envs_blacklist,
                'conda-gc-interval': self.conda_gc_interval
            }
        else:
            config['agent'] = {
                'restport': self.restport,
                'heartbeat-interval': self.heartbeat_interval,
                'services-file': self.services_file,
                'watch-interval': self.watch_interval,
                'bin-dir': self.bin_dir,
                'pid-file': self.pid_file,
                'agent-log-dir': self.agent_log_dir,
                'csr-log-file': self.csr_log_file,
                'logging-level': self.logging_level,
                'max-log-size': self.max_log_size,
                'mysql-socket': self.mysql_socket,
                'network-interface': self.network_interface,
                'group-name': self.group_name,
                'hadoop-home': self.hadoop_home,
                'certs-dir': self.certs_dir,
                'certificate-file': self.certificate_file,
                'key-file': self.key_file,
                'server-keystore': self.server_keystore,
                'server-truststore': self.server_truststore,
                'keystore-script': self.keystore_script,
                'state-store': self.state_store,
                'password': self.agent_password,
                'conda-dir': self.conda_dir,
                'conda-envs-blacklist': self.conda_envs_blacklist,
                'conda-gc-interval': self.conda_gc_interval
            }
            
        with open(self.config_file[1], 'w') as config_fd:
            config.write(config_fd)
        

    def _toUrl(self, path):
        return self.url + path

if __name__ == "__main__":
    unittest.main()
