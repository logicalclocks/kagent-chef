#!/usr/bin/env python
"""Script to register a new cluster host with Hopsworks and get a valid certificate"""

__author__="Jim Dowling <jdowling@kth.se> Antonios Kouzoupis <kouzoupis.ant@gmail.com>"

'''
Install:
 requests:    easy_install requests
 Netifaces:   easy_install netifaces
 IPy:         easy_install ipy
 pyOpenSSL:   apt-get install python-openssl
 MySQLdb:     apt-get install python-mysqldb
 pexpect:     apt-get install python-pexpect
'''

import sys
import logging
import logging.handlers
import os
import argparse
import requests
import json
import time
import subprocess

from OpenSSL import crypto
from os.path import join, exists

from kagent_utils import KConfig

class Certificate:
    """Class representing X509 certificate for host"""
    
    def __init__(self, config):
        self._config = config
        self._private_key = None
        self._certificate = None
        self._ca_certificate = None        
        
    def create_csr(self):
        """Generates a cryptographic key-pair and a CSR"""

        LOG.info("Creating Certificate Signing Request")
        pKey = self._generate_key()
        # Create CSR
        csr = crypto.X509Req()
        csr.get_subject().C = "SE"
        csr.get_subject().ST = "Sweden"
        csr.get_subject().L = "Stockholm"
        csr.get_subject().O = "Hopsworks"
        csr.get_subject().OU = "LC"

        # CN should be the hostname of the server
        _hostname = self._getHostname()
        LOG.debug("Hostname used in CN is {}".format(_hostname))
        csr.get_subject().CN = _hostname
        csr.set_pubkey(pKey)

        ### For kafka fix
        base_constraints = ([crypto.X509Extension("keyUsage", False, "Digital Signature, Non Repudiation, Key Encipherment")])
        x509_extensions = base_constraints
        # If there are SAN entries, append the base_constraints to include them.
        san_constraint = crypto.X509Extension("subjectAltName", False, "DNS: %s" % self._config.hostname)
        x509_extensions.append(san_constraint)
        csr.add_extensions(x509_extensions)
        ### End Kafka

        csr.sign(pKey, 'sha256')
        self.csr_req = crypto.dump_certificate_request(crypto.FILETYPE_PEM, csr)
        self._private_key = crypto.dump_privatekey(crypto.FILETYPE_PEM, pKey)
        LOG.debug("Finished CSR")

    def set_certificate(self, certificate):
        """Setter for a host certificate returned by Hopsworks"""
        self._certificate = certificate

    def set_ca_certificate(self, ca_certificate):
        """Setter for CA certificate returned by Hopsworks"""
        self._ca_certificate = ca_certificate

    def keystoresExist(self):
        """Checks if keystore, truststore and client_truststore exist in the predefined directory"""
        return exists(self._config.server_keystore) and exists(self._config.server_truststore)
    
    def store(self):
        """Write certificate and private key in current directory"""
        LOG.debug("Storing certificate, key and CA certificate")
        cert_dir = os.path.dirname(os.path.abspath(__file__))

        if self._ca_certificate is not None:
            with open(join(cert_dir, self._config.ca_file), "wt") as fd:
                fd.write(self._ca_certificate)
                
        if self._private_key is not None:
            with open(join(cert_dir, self._config.key_file), "wt") as fd:
                fd.write(self._private_key)

        if self._certificate is not None:
            with open(join(cert_dir, self._config.certificate_file), "wt") as fd:
                fd.write(self._certificate)
        LOG.info("Flushed crypto material to filesystem")
        
    def _generate_key(self):
        """Generates cryptographic pair"""

        LOG.debug("Generating cryptographic key-pair")
        pKey = crypto.PKey()
        pKey.generate_key(crypto.TYPE_RSA, 2048)
        
        return pKey
    
    def _getHostname(self):
        """Get and prepare host's hostname for CN"""
        hShort = self._config.hostname
        if (len(self._config.hostname) > 63):
            hShort = self._config.hostname[0:63]
            validEndChar = False
            offset = 63
            while (validEndChar == False):
                if (hShort[offset].isalnum()):
                    hShort = self._config.hostname[0:offset]
                    validEndChar = True
                offset -= 1
        return hShort


class Host:
    """Class representing a host in the cluster"""
    form_headers = {'Content-Type': 'application/x-www-form-urlencoded',
                     'User-Agent': 'hops-csr'}
    json_headers = {'User-Agent': 'Agent', 'content-type': 'application/json'}
    
    def __init__(self, conf, certificate):
        LOG.debug("Creating new host")
        self._conf = conf
        self._certificate = certificate

    def rotate_key(self, session, command_id):
        """Public method to perform key rotation"""
        self._rotate_key_internal(session, command_id)

    def _rotate_key_internal(self, session, command_id):
        self._login(session)
        payload = {}
        payload["csr"] = self._certificate.csr_req
        payload["agent-password"] = self._conf.agent_password
        payload["host-id"] = self._conf.host_id
        payload["id"] = command_id
        LOG.info("Rotating service key")
        LOG.debug("Rotation url is {0}".format(self._conf.rotate_url))
        response = session.post(self._conf.rotate_url, headers=self.json_headers, data=json.dumps(payload), verify=False)

        if (response.status_code != requests.codes.ok):
            raise Exception('Could not rotate service certificate Status code: {0} Reason: {1}'
                            .format(response.status_code, response.text))
        json_response = json.loads(response.content)
        self._extract_crypto_material(json_response)
    
    def register_host(self, session):
        """Public method to register a new host and sign its CSR"""
        registered = False
        while not registered:
            try :
                self._register_host_internal(session)
                registered = True
            except Exception, e:
                LOG.warning("Error while registering host {0}, will try again in {1} seconds..."
                            .format(e, self._conf.heartbeat_interval))
                time.sleep(self._conf.heartbeat_interval)

    def _register_host_internal(self, session):
        self._login(session)
        payload = {}
        payload["csr"] = self._certificate.csr_req
        payload["agent-password"] = self._conf.agent_password
        payload["host-id"] = self._conf.host_id
        LOG.info("Registering with Hopsworks")
        response = session.post(self._conf.register_url, headers=self.json_headers, data=json.dumps(payload), verify=False)

        if (response.status_code != requests.codes.ok):
            raise Exception('Could not register: Unknown host id or internal error on the dashboard (Status code: {0} - {1}).'
                            .format(response.status_code, response.text))

        json_response = json.loads(response.content)
        self._extract_crypto_material(json_response)
        
        hadoopHome = json_response["hadoopHome"]
        self._conf.set_conf_value('agent', 'hadoop-home', hadoopHome)
        self._conf.dump_to_file()

    def _extract_crypto_material(self, json_response):
        """Extract crypto material from the response from hopsworks-ca and write them locally"""
        certificate = json_response["pubAgentCert"]
        caCertificate = json_response["caPubCert"]
        self._certificate.set_certificate(certificate)
        self._certificate.set_ca_certificate(caCertificate)
        self._certificate.store()
        
    def _login(self, session):
        """Helper method to login to Hopsworks"""
        login_payload = {'email': self._conf.server_username, 'password': self._conf.server_password}
        # First login
        LOG.debug("Logging in to Hopsworks")
        response = session.post(self._conf.login_url, headers=self.form_headers, data=login_payload, verify=False)
        if (response.status_code != requests.codes.ok):
            raise Exception('Could not login to Hopsworks')

        LOG.debug("Logged in successfully")        

        
def setup_logging(log_file, max_log_size, logLevel):
    """Setup logging utilities"""
    global LOG
    LOG = logging.getLogger('csr-agent')
    LOG.setLevel(logLevel)
    file_handler = logging.handlers.RotatingFileHandler(log_file, mode='a', maxBytes=max_log_size, backupCount=5)
    file_handler.setLevel(logLevel)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logLevel)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    LOG.addHandler(file_handler)
    LOG.addHandler(console_handler)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logLevel)
    requests_log.propagate = True


    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Register host with Hopsworks and get certificate.')

    parser.add_argument('-c', '--config', default='config.ini', help='Configuration file')

    subparser = parser.add_subparsers(dest='operation', help='Operations')
    parser_i = subparser.add_parser('init', help='Initialize agent')

    parser_r = subparser.add_parser('rotate', help='Rotate node certificate')
    parser_r.add_argument('-c', '--commandid', help='Command ID from Hopsworks', default='-1')

    args = parser.parse_args()

    config = KConfig(args.config)
    config.read_conf()
    setup_logging(config.csr_log_file, config.max_log_size, config.logging_level)
    LOG.info("Hops CSR-agent started.")
    LOG.info("Register URL: {0}".format(config.register_url))
    LOG.info("Public IP: {0}".format(config.public_ip))
    LOG.info("Private IP: {0}".format(config.private_ip))

    agent_pid = str(os.getpid())
    file(config.agent_pidfile, 'w').write(agent_pid)
    LOG.info("Hops CSR-agent PID: {0}".format(agent_pid))

    cert = Certificate(config)
    if args.operation == "init":
        LOG.debug("Initializing")
        
        if cert.keystoresExist():
            LOG.warning("Keystores already exist, aborting initializing")
            sys.exit(2)
            
        cert.create_csr()

        h = Host(config, cert)
        with requests.Session() as session:
            try:
                h.register_host(session)
                subprocess.check_call(config.keystore_script)
            except Exception, e:
                LOG.error("Error while registering host: {0}".format(e))
                raise e
            
    elif args.operation == "rotate":
        LOG.debug("Key rotation")

        cert.create_csr()
        h = Host(config, cert)
        with requests.Session() as session:
            try:
                h.rotate_key(session, args.commandid)
                subprocess.call(config.keystore_script)
            except Exception, e:
                LOG.error("Error while rotating key: {0}".format(e))
                raise e
    
