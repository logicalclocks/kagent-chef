include_attribute "conda"

# Default values for configuration parameters
default["kagent"]["version"]                       = node["install"]["version"]
default["kagent"]["user"]                          = node["install"]["user"].empty? ? "kagent" : node["install"]["user"]
default["kagent"]["group"]                         = node["install"]["user"].empty? ? "kagent" : node["install"]["user"]
default["kagent"]["user-home"]                     = "/home/#{node["kagent"]["user"]}"

default["kagent"]["certs_group"]                   = "certs"
default["kagent"]["certs_user"]                    = "certs"

# Less privileged group for accessing users certificates in transient/
default["kagent"]["userscerts_group"]              = "userscerts"

default["kagent"]["dir"]                           = node["install"]["dir"].empty? ? "/var/lib/kagent" : node["install"]["dir"] + "/kagent"
default["kagent"]["base_dir"]                      = "#{node["kagent"]["dir"]}/kagent"
default["kagent"]["home"]                          = "#{node["kagent"]["dir"]}/kagent-#{node["kagent"]["version"]}"
default["kagent"]["etc"]                           = "#{node["kagent"]["dir"]}/etc"
default['kagent']['state_store']                   = "#{node['kagent']['etc']}/state_store"
default['kagent']['logs']                          = "#{node['kagent']['dir']}/logs"
default['csr']['log-file']                         = "#{node["kagent"]["certs_dir"]}/csr.log"

# Data volume directories
default['kagent']['data_volume']['root_dir']       = "#{node['data']['dir']}/kagent"
default['kagent']['data_volume']['state_store']    = "#{node['kagent']['data_volume']['root_dir']}/state_store"
default['kagent']['data_volume']['logs']           = "#{node['kagent']['data_volume']['root_dir']}/logs"
default['csr']['data_volume']['logs']              = "#{node['data']['dir']}/csr_logs"
default['csr']['data_volume']['log-file']          = "#{node['csr']['data_volume']['logs']}/csr.log"
default['certs']['data_volume']['dir']             = "#{node['data']['dir']}/certs-dir"
default['x509']['data_volume']['super-crypto-dir'] = "#{node['data']['dir']}/super_crypto"

default["kagent"]["enabled"]                       = "true"

default["kagent"]["certs_dir"]                     = "#{node["kagent"]["dir"]}/host-certs"

# API calls
default["kagent"]["dashboard"]["api"]["register"]  = "api/agentresource?action=register"
default["kagent"]["dashboard"]["api"]["login"]     = "api/auth/service"
default["kagent"]["dashboard"]["api"]["ca_host"]   = "v2/certificate/host"
default["kagent"]["dashboard"]["api"]["heartbeat"] = "api/agentresource?action=heartbeat"
default["kagent"]["dashboard"]["api"]["alert"]     = "api/agentresource/alert"

# Username/Password for the dashboard connecting to Hopsworks
default["kagent"]["dashboard"]["user"]             = "agent@hops.io"
default["kagent"]["dashboard"]["password"]         = "admin"

# Username/Password for the keystore

default["hopsworks"]["master"]["password"]         = "adminpw"

# Agent's local certificate for SSL connections
default["kagent"]["certificate_file"]              = "server.pem"

# dashboard ip:port endpoint
default["kagent"]["dashboard_app"]                 = "hopsworks-api"
default["kagent"]["ca_app"]                        = "hopsworks-ca"

# local settings for agent
default["kagent"]["port"]                          = 8090
default["kagent"]["heartbeat_interval"]            = 3
default["kagent"]["watch_interval"]                = "2s"
default["kagent"]["pid_file"]                      = node["kagent"]["dir"] + "/kagent.pid"
default["kagent"]["logging_level"]                 = "INFO"
default["kagent"]["max_log_size"]                  = "10000000"

default["kagent"]["network"]["interface"]          = ""

default["kagent"][:default][:public_ips]              = ['10.0.2.15']
default["kagent"][:default][:private_ips]             = ['10.0.2.15']
default["kagent"][:default][:gateway_ips]             = ['10.0.2.2']

# services file contains locally installed services

default["kagent"]["services"]                      = node["kagent"]["etc"] + "/services"

default["kagent"]["hostid"]                        = 100

default["kagent"]["password"]                      = ""

default["kagent"]["dns"]                           = "false"

default["public_ips"]                              = ['10.0.2.15']
default["private_ips"]                             = ['10.0.2.15']
default["gateway_ips"]                             = ['10.0.2.2']

default["systemd"]                            = "true"

default["vagrant"]                            = "false"

default["ntp"]["install"]                     = "false"
# Servers to sync ntp time with
# '0.pool.ntp.org', '1.pool.ntp.org'
normal["ntp"]["servers"]                      = ['0.europe.pool.ntp.org', '1.europe.pool.ntp.org', '2.europe.pool.ntp.org', '3.europe.pool.ntp.org']

normal["ntp"]["peers"]                        = ['time0.int.example.org', 'time1.int.example.org']

default["services"]["enabled"]                     = "true"

default["certs"]["dir"]                            = node["install"]["dir"].empty? ? node["kagent"]["dir"] + "/certs-dir" : node["install"]["dir"] + "/certs-dir"

default["java"]["install_flavor"]                  = "openjdk"
default["java"]["jdk_version"]                     = 8

default["kagent"]["hopsify"]["version"]            = "0.3.0"
default["kagent"]["hopsify"]["bin_url"]            = "#{node['download_url']}/hopsify/amd64/#{node['kagent']['hopsify']['version']}/hopsify"
default['x509']['super-crypto']['base-dir']        = "/srv/hops/super_crypto"
default['x509']['super-crypto']['dir']             = "#{node['x509']['super-crypto']['base-dir']}/${USER}"
default['x509']['keystores']['keystore']           = "${USERNAME}__kstore.jks"
default['x509']['keystores']['truststore']         = "${USERNAME}__tstore.jks"
default['x509']['private']['pkcs8']                = "${USERNAME}_priv.pem"
default['x509']['private']['pkcs1']                = "${USERNAME}_priv.pem.rsa"
default['x509']['public']                          = "${USERNAME}_pub.pem"
default['x509']['certificate-bundle']              = "${USERNAME}_certificate_bundle.pem"
default['x509']['ca']['root']                      = "hops_root_ca.pem"
default['x509']['ca']['intermediate']              = "hops_intermediate_ca.pem"
default['x509']['ca']['bundle']                    = "hops_ca_bundle.pem"


default['kagent']['cloud']['monitor_interval']     = 3
default['kagent']['cloud']['monitor_url']          = ""