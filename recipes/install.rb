######################################
## Do sanity checks here, fail fast ##
######################################

if node['kernel']['machine'] != 'x86_64'
  Chef::Log.fatal!("Unrecognized node.kernel.machine=#{node['kernel']['machine']}; Only x86_64", 1)
end

# If FQDN is longer than 63 characters fail HOPSWORKS-1075
fqdn = node['fqdn']
raise "FQDN #{fqdn} is too long! It should not be longer than 60 characters" unless fqdn.length < 61

# If installing EE check that everything is set
if node['install']['enterprise']['install'].casecmp? "true"
  if not node['install']['enterprise']['download_url']
    raise "Installing Hopsworks EE but install/enterprise/download_url is not set"
  end
  if node['install']['enterprise']['username'] and not node['install']['enterprise']['password']
    raise "Installing Hopsworks EE, username is set but not password"
  end
  if node['install']['enterprise']['password'] and not node['install']['enterprise']['username']
    raise "Installing Hopsworks EE, password is set but not username"
  end
end

case node["platform_family"]
when "debian"
  package ["python3-venv", "build-essential", "libssl-dev", "jq", "acl"] do
    retries 10
    retry_delay 30
  end

# Change lograte policy
  cookbook_file '/etc/logrotate.d/rsyslog' do
    source 'rsyslog.ubuntu'
    owner 'root'
    group 'root'
    mode '0644'
  end

  # Ubuntu comes with unattended-upgrades package pre-install which
  # automatically upgrades installed packages
  # Disable it as it can/will upgrade a package to a version we don't
  # support.
  # Also, as a side-effect when run it stops the docker daemon
  systemd_unit "apt-daily-upgrade.timer" do
    action [:stop, :disable]
  end
  package 'unattended-upgrades' do
    retries 10
    retry_delay 30
    action :remove
  end

when "rhel"

  if node['rhel']['epel'].downcase == "true"
    package "epel-release" do
      retries 10
      retry_delay 30
    end
  end

  # gcc, gcc-c++, kernel-devel are the equivalent of "build-essential" from apt.
  # see the comment in tensorflow::install for the explanation on what's going on here.
  package 'kernel-devel' do
    version node['kernel']['release'].sub(/\.#{node['kernel']['machine']}/, "")
    arch node['kernel']['machine']
    action :install
    ignore_failure true
  end

  package 'kernel-devel' do
    retries 10
    retry_delay 30
    action :install
    not_if  "ls -l /usr/src/kernels/$(uname -r)"
  end

  package ["python3-virtualenv", "gcc", "gcc-c++", "openssl", "openssl-devel", "openssl-libs", "jq"] do
    retries 10
    retry_delay 30
  end

  # Change lograte policy
  cookbook_file '/etc/logrotate.d/syslog' do
    source 'syslog.centos'
    owner 'root'
    group 'root'
    mode '0644'
  end
end

group node["kagent"]["group"] do
  gid node['kagent']['group_id']
  action :create
  not_if "getent group #{node["kagent"]["group"]}"
  not_if { node['install']['external_users'].casecmp("true") == 0 }
end

group node["kagent"]["certs_group"] do
  gid node['kagent']['certs_group_id']
  action :create
  not_if "getent group #{node["kagent"]["certs_group"]}"
  not_if { node['install']['external_users'].casecmp("true") == 0 }
end

user node["kagent"]["certs_user"] do
  uid node['kagent']['certs_user_id']
  gid node["kagent"]["certs_group"]
  action :create
  manage_home false
  system true
  shell "/bin/nologin"
  not_if "getent passwd #{node["kagent"]["certs_user"]}"
  not_if { node['install']['external_users'].casecmp("true") == 0 }
end

user node["kagent"]["user"] do
  uid node['kagent']['user_id']
  gid node["kagent"]["group"]
  action :create
  manage_home true
  home node['kagent']['user-home']
  shell "/bin/bash"
  system true
  not_if "getent passwd #{node["kagent"]["user"]}"
  not_if { node['install']['external_users'].casecmp("true") == 0 }
end

group node["kagent"]["group"] do
  action :modify
  # Certs user is in the kagnet group so it can also modify the Kagent state store.
  members [node["kagent"]["user"], node["kagent"]["certs_user"]]
  append true
  not_if { node['install']['external_users'].casecmp("true") == 0 }
end

group node["kagent"]["certs_group"] do
  action :modify
  members ["#{node["kagent"]["user"]}"]
  append true
  not_if { node['install']['external_users'].casecmp("true") == 0 }
end

group "video"  do
  action :modify
  members ["#{node["kagent"]["user"]}"]
  append true
  not_if { node['install']['external_users'].casecmp("true") == 0 }
end

chef_gem "inifile" do
  action :install
end

directory node["kagent"]["dir"]  do
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode "755"
  recursive true
  action :create
  not_if { File.directory?("#{node["kagent"]["dir"]}") }
end

directory node['install']['dir'] do
  owner 'root'
  group 'root'
  mode '0755'
  action :create
  not_if { ::File.directory?(node['install']['dir']) }
end

directory node['data']['dir'] do
  owner 'root'
  group 'root'
  mode '0775'
  action :create
  not_if { ::File.directory?(node['data']['dir']) }
end

directory node['kagent']['data_volume']['root_dir']  do
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode "755"
  action :create
  not_if { File.directory?("#{node['kagent']['data_volume']['root_dir']}") }
end

directory node['kagent']['data_volume']['logs']  do
  owner node['kagent']['user']
  group node['kagent']['group']
  mode "755"
  action :create
  not_if { File.directory?("#{node['kagent']['data_volume']['logs']}") }
end

bash 'Move kagent logs to data volume' do
  user 'root'
  code <<-EOH
    set -e
    mv -f #{node['kagent']['logs']}/* #{node['kagent']['data_volume']['logs']}
    mv -f #{node['kagent']['logs']} #{node['kagent']['logs']}_deprecated
  EOH
  only_if { conda_helpers.is_upgrade }
  only_if { File.directory?(node['kagent']['logs'])}
  not_if { File.symlink?(node['kagent']['logs'])}
end

link node['kagent']['logs'] do
  owner node['kagent']['user']
  group node['kagent']['group']
  mode '0755'
  to node['kagent']['data_volume']['logs']
end

directory node['csr']['data_volume']['logs']  do
  owner node['kagent']['certs_user']
  group node['kagent']['group']
  mode "750"
  action :create
  not_if { File.directory?(node['csr']['data_volume']['logs']) }
end

## Fix bug with wrong path to csr.log
link '/csr.log' do
  action :delete
  only_if { conda_helpers.is_upgrade }
  only_if { File.symlink?('/csr.log') }
end

directory node["kagent"]["certs_dir"] do
  owner node["kagent"]["certs_user"]
  group node["kagent"]["certs_group"]
  mode "750"
  action :create
end

bash 'Move CSR log file to data volume' do
  user 'root'
  code <<-EOH
    set -e
    mv -f #{node['csr']['log-file']} #{node['csr']['data_volume']['log-file']}
  EOH
  only_if { conda_helpers.is_upgrade }
  only_if { File.exist?(node['csr']['log-file'])}
  not_if { File.symlink?(node['csr']['log-file']) }
end

file node['csr']['data_volume']['log-file'] do
  content ''
  owner node['kagent']['certs_user']
  group node['kagent']['group']
  mode "750"
  action :create
  not_if { File.exist?(node['csr']['data_volume']['log-file']) }
end

link node['csr']['log-file'] do
  owner node['kagent']['certs_user']
  group node['kagent']['group']
  mode "750"
  to node['csr']['data_volume']['log-file']
end

directory node['kagent']['etc']  do
  owner node['kagent']['user']
  group node['kagent']['group']
  mode "755"
  action :create
  not_if { File.directory?(node['kagent']['etc']) }
end

directory node['kagent']['data_volume']['state_store'] do
  owner node['kagent']['user']
  group node['kagent']['group']
  mode '0770'
  action :create
  not_if { File.directory?(node['kagent']['data_volume']['state_store'])}
end

bash 'Move CSR state store to data volume' do
  user 'root'
  code <<-EOH
    set -e
    mv -f #{node['kagent']['state_store']}/* #{node['kagent']['data_volume']['state_store']}
    mv -f #{node['kagent']['state_store']} #{node['kagent']['state_store']}_deprecated
  EOH
  only_if { conda_helpers.is_upgrade }
  only_if { File.directory?(node['kagent']['state_store'])}
  not_if { File.symlink?(node['kagent']['state_store']) }
end

link node['kagent']['state_store'] do
  owner node['kagent']['user']
  group node['kagent']['group']
  mode '0770'
  to node['kagent']['data_volume']['state_store']
end


directory node["kagent"]["home"] do
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode "750"
  action :create
end

link node["kagent"]["base_dir"] do
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  to node["kagent"]["home"]
end

directory "#{node["kagent"]["home"]}/bin" do
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode "755"
  action :create
end

file node["kagent"]["services"] do
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode "755"
  action :create_if_missing
end

if node["ntp"]["install"] == "true"
  include_recipe "ntp::default"
end

remote_directory "#{Chef::Config['file_cache_path']}/kagent_utils" do
  source 'kagent_utils'
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode 0710
  files_owner node["kagent"]["user"]
  files_group node["kagent"]["group"]
  files_mode 0710
end

cookbook_file "#{node["kagent"]["home"]}/agent.py" do
  source 'agent.py'
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode 0710
end

directory node['x509']['data_volume']['super-crypto-dir'] do
  owner node['kagent']['certs_user']
  group node['kagent']['certs_group']
  mode 0755
end

bash 'Move super users certificates to data volume' do
  user 'root'
  code <<-EOH
    set -e
    mv -f #{node['x509']['super-crypto']['base-dir']}/* #{node['x509']['data_volume']['super-crypto-dir']}
    rmdir #{node['x509']['super-crypto']['base-dir']}
  EOH
  only_if { conda_helpers.is_upgrade }
  only_if { File.directory?(node['x509']['super-crypto']['base-dir'])}
  not_if { File.symlink?(node['x509']['super-crypto']['base-dir'])}
end

link "#{node['x509']['super-crypto']['base-dir']}" do
  owner node["kagent"]["certs_user"]
  group node["kagent"]["certs_group"]
  mode 0755
  to node['x509']['data_volume']['super-crypto-dir']
end

basename = File.basename(node['kagent']['hopsify']['bin_url'])
remote_file "#{node["kagent"]["certs_dir"]}/#{basename}" do
    user node['kagent']['certs_user']
    group node['kagent']['certs_group']
    source node['kagent']['hopsify']['bin_url']
    mode 0550
    action :create
end

template "#{node["kagent"]["home"]}/bin/start-all-local-services.sh" do
  source "start-all-local-services.sh.erb"
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode 0740
end

template "#{node["kagent"]["home"]}/bin/shutdown-all-local-services.sh" do
  source "shutdown-all-local-services.sh.erb"
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode 0740
end

template "#{node["kagent"]["home"]}/bin/status-all-local-services.sh" do
  source "status-all-local-services.sh.erb"
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode 0740
end

kagent_home = conda_helpers.get_user_home(node['kagent']['user'])

directory "#{kagent_home}/.pip" do
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode '0700'
  action :create
end

template "#{kagent_home}/.pip/pip.conf" do
  source "pip.conf.erb"
  cookbook "conda"
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode 0750
  action :create
end

cookbook_file "#{node["kagent"]["dir"]}/requirements.txt"  do
  source "requirements.txt"
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode "755"
end

directory node["kagent"]["virtualenv"] do 
  user node["kagent"]["user"]
  recursive true
  action :delete
  only_if { File.directory?(node["kagent"]["virtualenv"]) }
end

bash 'Create Kagent virtualenv' do 
  user node["kagent"]["user"]
  cwd node["kagent"]["base_dir"]
  environment ({'HOME' => kagent_home})
  code <<-EOH
    set -e
    python3 -m venv #{node["kagent"]["virtualenv"]}
    #{node["kagent"]["virtualenv"]}/bin/pip install -r #{node["kagent"]["dir"]}/requirements.txt
    #{node["kagent"]["virtualenv"]}/bin/pip install #{Chef::Config['file_cache_path']}/kagent_utils
  EOH
end
  
