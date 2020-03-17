import unittest
import configparser
import os
import tempfile
import socket

from kagent_utils import KConfig


class TestKConfig(unittest.TestCase):

    # server section
    url = 'http://localhost:1337/'
    path_login = 'login/path'
    path_register = 'register/path'
    path_ca_host = 'ca/host/path'
    path_heartbeat = 'heartbeat/path'
    username = 'username'
    server_password = 'server_password'

    # agent section
    host_id = 'host_0'
    restport = '8080'
    heartbeat_interval = '3'
    services_file = 'path/to/services/file'
    watch_interval = '4s'
    bin_dir = 'path/to/bin/dir'
    sbin_dir = 'path/to/sbin/dir'
    pid_file = 'path/to/pid/file'
    agent_log_dir = 'path/to/agent/logs'
    csr_log_file = 'path/to/csr/log_file'
    logging_level = 'DEBUG'
    max_log_size = '100'
    hostname = 'myhostname'
    hadoop_home = 'path/to/hadoop_home'
    certs_dir = 'path/to/certs_dir'
    certs_user = 'cert_user'
    keystore_script = 'path/to/keystore_script'
    state_store = 'path/to/state_store'
    agent_password = 'agent_password'
    private_ip = '127.0.0.1'
    public_ip = '192.168.0.1'
    
    def setUp(self):
        self.config_file = tempfile.mkstemp(prefix='kagent_config_')

    def tearDown(self):
        os.remove(self.config_file[1])

    def test_parse_full_config(self):
        self._prepare_config_file(True)

        config = KConfig(self.config_file[1])
        config.load()
        config.read_conf()

        self.assertEqual(self.url, config.server_url)
        self.assertEqual(self._toUrl(self.path_login), config.login_url)
        self.assertEqual(self._toUrl(self.path_register), config.register_url)
        self.assertEqual(self._toUrl(self.path_ca_host), config.ca_host_url)
        self.assertEqual(self._toUrl(self.path_heartbeat), config.heartbeat_url)
        self.assertEqual(self.username, config.server_username)
        self.assertEqual(self.server_password, config.server_password)
        self.assertEqual(self.host_id, config.host_id)
        self.assertEqual(int(self.restport), config.rest_port)
        self.assertEqual(int(self.heartbeat_interval), config.heartbeat_interval)
        self.assertEqual(self.services_file, config.services_file)
        self.assertEqual(self.watch_interval, config.watch_interval)
        self.assertEqual(self.bin_dir, config.bin_dir)
        self.assertEqual(self.sbin_dir, config.sbin_dir)
        self.assertEqual(self.pid_file, config.agent_pidfile)
        self.assertEqual(self.agent_log_dir, config.agent_log_dir)
        self.assertEqual(self.csr_log_file, config.csr_log_file)
        self.assertEqual(self.logging_level, config.logging_level_str)
        self.assertEqual(int(self.max_log_size), config.max_log_size)
        self.assertEqual(self.private_ip, config.private_ip)
        self.assertEqual(self.public_ip, config.public_ip)
        self.assertEqual(self.hostname, config.hostname)
        self.assertEqual(self.hadoop_home, config.hadoop_home)
        self.assertEqual(self.certs_dir, config.certs_dir)
        self.assertEqual(self.certs_user, config.certs_user)
        self.assertEqual(self.keystore_script, config.keystore_script)
        self.assertEqual(self.state_store, config.state_store_location)
        self.assertEqual(self.agent_password, config.agent_password)
        
    # Let KConfig figure out values for these properties
    def test_parse_partial_config(self):
        self._prepare_config_file(False)
        config = KConfig(self.config_file[1])
        config.load()
        config.read_conf()

        self.assertIsNotNone(config.agent_password)
        self.assertNotEqual('', config.agent_password)

        my_hostname = socket.gethostbyaddr(self.private_ip)[0]
        self.assertEqual(my_hostname, config.hostname)

        self.assertEqual(my_hostname, config.host_id)

    def test_alternate_host(self):
        alternate_host = "https://alternate.url:443/"
        self._prepare_config_file(False)
        config = KConfig(self.config_file[1])
        config.load()
        config.server_url = alternate_host
        config.read_conf()

        self.assertEqual(alternate_host, config.server_url)
        register_path = config._config.get('server', 'path-register')
        self.assertEqual(alternate_host + register_path, config.register_url)

    def _prepare_config_file(self, all_keys):
        config = configparser.ConfigParser()

        config['server'] = {
            'url': self.url,
            'path-login': self.path_login,
            'path-register': self.path_register,
            'path-ca-host': self.path_ca_host,
            'path-heartbeat': self.path_heartbeat,
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
                'sbin-dir': self.sbin_dir,
                'pid-file': self.pid_file,
                'agent-log-dir': self.agent_log_dir,
                'csr-log-file': self.csr_log_file,
                'logging-level': self.logging_level,
                'max-log-size': self.max_log_size,
                'hostname': self.hostname,
                'hadoop-home': self.hadoop_home,
                'certs-dir': self.certs_dir,
                'certs-user': self.certs_user,
                'keystore-script': self.keystore_script,
                'state-store': self.state_store,
                'password': self.agent_password,
                'private-ip': self.private_ip,
                'public-ip': self.public_ip,
            }
        else:
            config['agent'] = {
                'restport': self.restport,
                'heartbeat-interval': self.heartbeat_interval,
                'services-file': self.services_file,
                'watch-interval': self.watch_interval,
                'bin-dir': self.bin_dir,
                'sbin-dir': self.sbin_dir,
                'pid-file': self.pid_file,
                'agent-log-dir': self.agent_log_dir,
                'csr-log-file': self.csr_log_file,
                'logging-level': self.logging_level,
                'max-log-size': self.max_log_size,
                'hadoop-home': self.hadoop_home,
                'certs-dir': self.certs_dir,
                'certs-user': self.certs_user,
                'keystore-script': self.keystore_script,
                'state-store': self.state_store,
                'password': self.agent_password,
                'private-ip': self.private_ip,
                'public-ip': self.public_ip,
            }

        with open(self.config_file[1], 'w') as config_fd:
            config.write(config_fd)

    def _toUrl(self, path):
        return self.url + path


if __name__ == "__main__":
    unittest.main()
