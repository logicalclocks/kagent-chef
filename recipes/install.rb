######################################
## Do sanity checks here, fail fast ##
######################################

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
  package ["python2.7", "python2.7-dev", "build-essential", "libssl-dev", "jq"]

# Change lograte policy
  cookbook_file '/etc/logrotate.d/rsyslog' do
    source 'rsyslog.ubuntu'
    owner 'root'
    group 'root'
    mode '0644'
  end

when "rhel"

  if node['rhel']['epel'].downcase == "true"
    package "epel-release"
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
    action :install
    not_if  "ls -l /usr/src/kernels/$(uname -r)"
  end

  package ["gcc", "gcc-c++", "openssl", "openssl-devel", "openssl-libs", "python", "python-pip", "python-devel", "jq"]

  # Change lograte policy
  cookbook_file '/etc/logrotate.d/syslog' do
    source 'syslog.centos'
    owner 'root'
    group 'root'
    mode '0644'
  end
end

group node["kagent"]["group"] do
  action :create
  not_if "getent group #{node["kagent"]["group"]}"
  not_if { node['install']['external_users'].casecmp("true") == 0 }
end

group node["kagent"]["certs_group"] do
  action :create
  not_if "getent group #{node["kagent"]["certs_group"]}"
  not_if { node['install']['external_users'].casecmp("true") == 0 }
end

user node["kagent"]["certs_user"] do
  gid node["kagent"]["certs_group"]
  action :create
  manage_home false
  system true
  shell "/bin/nologin"
  not_if "getent passwd #{node["kagent"]["certs_user"]}"
  not_if { node['install']['external_users'].casecmp("true") == 0 }
end

user node["kagent"]["user"] do
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

bash "make_gemrc_file" do
  user "root"
  code <<-EOF
   echo "gem: --no-ri --no-rdoc" > ~/.gemrc
 EOF
  not_if "test -f ~/.python_libs_installed"
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

directory node["kagent"]["etc"]  do
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode "755"
  action :create
  not_if { File.directory?("#{node["kagent"]["etc"]}") }
end

directory "#{node["kagent"]["etc"]}/state_store" do
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode "770"
  action :create
  not_if { File.directory?("#{node["kagent"]["etc"]}/state_store") }
end

directory node["kagent"]["home"] do
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode "750"
  action :create
end

directory node["kagent"]["certs_dir"] do
  owner node["kagent"]["certs_user"]
  group node["kagent"]["certs_group"]
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

directory "#{node['x509']['super-crypto']['base-dir']}" do
  owner node["kagent"]["certs_user"]
  group node["kagent"]["certs_group"]
  mode 0755
  action :create
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

