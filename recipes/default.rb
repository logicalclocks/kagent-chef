require 'inifile'
require 'securerandom'

service_name = "kagent"

agent_password = ""


# First try to read from Chef attributes
if node["kagent"]["password"].empty? == false
 agent_password = node["kagent"]["password"]
end

# If agent password has not been overwritten try to read it from a previous
# configuration file, in case of an update
if ::File.exists?("#{node["kagent"]["etc"]}/config.ini") && agent_password.empty?
  ini_file = IniFile.load("#{node["kagent"]["etc"]}/config.ini", :comment => ';#')
  if ini_file.has_section?("agent")
    agent_password = "#{ini_file["agent"]["password"]}"
  end
end  

# Otherwise generate a random password
if agent_password.empty?
  agent_password = SecureRandom.hex[0...10]
end



if node['install']['gce'] == "true" || node['install']['aws'] == "true" || node['install']['azure'] == "true" 
  template "#{node['kagent']['base_dir']}/bin/edit-config-ini-inplace.py" do
    source "edit-config-ini-inplace.py.erb"
    owner node['kagent']['user']
    group node['kagent']['group']
    mode 0744
  end

  template "#{node['kagent']['base_dir']}/bin/edit-and-start.sh" do
    source "edit-and-start.sh.erb"
    owner node['kagent']['user']
    group node['kagent']['group']
    mode 0744
  end

  
end


case node[:platform]
when "ubuntu"
 if node[:platform_version].to_f <= 14.04
   node.default["systemd"] = "false"
 end
end

if node[:systemd] == "true"
  service "#{service_name}" do
    provider Chef::Provider::Service::Systemd
    supports :restart => true, :start => true, :stop => true, :enable => true
    action :nothing
  end


  case node[:platform_family]
  when "rhel"
    systemd_script = "/usr/lib/systemd/system/#{service_name}.service"    
  else # debian
    systemd_script = "/lib/systemd/system/#{service_name}.service"
  end

  template systemd_script do
    source "#{service_name}.service.erb"
    owner "root"
    group "root"
    mode 0755
    if node["services"]["enabled"] == "true"
     notifies :enable, resources(:service => service_name)
    end
    notifies :restart, "service[#{service_name}]", :delayed
  end

# Creating a symlink causes systemctl enable to fail with too many symlinks
# https://github.com/systemd/systemd/issues/3010

  kagent_config service_name do
    action :systemd_reload
  end
  
else # sysv

  service "#{service_name}" do
    provider Chef::Provider::Service::Init::Debian
    supports :restart => true, :start => true, :stop => true, :enable => true
    action :nothing
  end
  
  template "/etc/init.d/#{service_name}" do
    source "#{service_name}.erb"
    owner "root"
    group "root"
    mode 0755
if node["services"]["enabled"] == "true"
    notifies :enable, resources(:service => service_name)
end
    notifies :restart, "service[#{service_name}]", :delayed
  end

  kagent_config do
    action :systemd_reload
  end
  
end

private_ip = my_private_ip()
public_ip = my_public_ip()

dashboard_endpoint = private_recipe_ip("hopsworks","default")  + ":8181" 
if node.attribute? "hopsworks"
  if node["hopsworks"].attribute? "https" and node["hopsworks"]['https'].attribute? ('port')
    dashboard_endpoint = private_recipe_ip("hopsworks","default")  + ":" + node['hopsworks']['https']['port']
  end
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

# Default to hostname found in /etc/hosts, but allow user to override it.
# First with DNS. Highest priority if user supplies the actual hostname
hostname = node['fqdn']

if node["kagent"].attribute?("hostname")
  if node["kagent"]["hostname"].empty? == false
    hostname = node["kagent"]["hostname"]
  end
else
  if node['install']['localhost'].casecmp?("true")
    hostname = "localhost"
  end
end

Chef::Log.info "Hostname to register kagent in config.ini is: #{hostname}"
if hostname.empty?
  raise "Hostname in kagent/config.ini cannot be empty"
end

#
# Certificate Signing code - Needs Hopsworks dashboard
#

template "#{node["kagent"]["home"]}/keystore.sh" do
  source "keystore.sh.erb"
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode 0700
  variables({
              :fqdn => hostname,
              :directory => node["kagent"]["keystore_dir"],
              :keystorepass => node["hopsworks"]["master"]["password"]
            })
end

# Default to hostname found in /etc/hosts, but allow user to override it.
# First with DNS. Highest priority if user supplies the actual hostname


hops_dir=node['install']['dir']
if node.attribute?("hops") && node["hops"].attribute?("dir") 
  hops_dir=node['hops']['dir'] + "/hadoop"
end
if hops_dir == "" 
 # Guess that it is the default value
 hops_dir = node['install']['dir'] + "/hadoop"
end

## blacklisted_envs is a comma separated list of Anaconda environments
## that should not be deleted by Conda GC
# python envs
blacklisted_envs = node['kagent']['python_conda_versions'].split(",").map(&:strip)
                     .map {|p| p.gsub(".", "") }.map {|p| "python" + p}.join(",")
# hops-system anaconda env
blacklisted_envs += ",hops-system,airflow"

template "#{node["kagent"]["etc"]}/config.ini" do
  source "config.ini.erb"
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode 0600
  action :create
  variables({
              :rest_url => "https://#{dashboard_endpoint}/",
              :rack => '/default',
              :hostname => hostname,
              :public_ip => public_ip,
              :private_ip => private_ip,
              :hops_dir => hops_dir,
              :agent_password => agent_password,
              :kstore => "#{node["kagent"]["keystore_dir"]}/#{hostname}__kstore.jks",
              :tstore => "#{node["kagent"]["keystore_dir"]}/#{hostname}__tstore.jks",
              :blacklisted_envs => blacklisted_envs
            })
  
if node["services"]["enabled"] == "true"  
  notifies :enable, "service[#{service_name}]"
end
  notifies :restart, "service[#{service_name}]", :delayed
end

if node["kagent"]["test"] == false && node['install']['upgrade'] == "false"
    kagent_keys "sign-certs" do
       action :csr
    end
end

execute "rm -f #{node["kagent"]["pid_file"]}"

if node["kagent"]["cleanup_downloads"] == 'true'

  file "/tmp/#{d}*.tgz" do
    action :delete
    ignore_failure true
  end

end

if node["install"]["addhost"] == 'true'

  #
  # This code will wipe out the existing anaconda installation and replace it with one from the hopsworks server - using rsync.
  # You should remove the anaconda base_dir (/srv/hops/anaconda/anaconda) and set the attribute install/addhost='true' for this to run.
  #
 bash "sync-anaconda-with-existing-cluster" do
   user "root"
   code <<-EOH
     #{node['kagent']['base_dir']}/bin/anaconda_sync.sh
   EOH
   not_if { File.directory?("#{node['conda']['base_dir']}") }
 end
  
end  


homedir = node['kagent']['user'].eql?("root") ? "/root" : "/home/#{node['kagent']['user']}"
kagent_keys "#{homedir}" do
  cb_user "#{node['kagent']['user']}"
  cb_group "#{node['kagent']['group']}"
  cb_name "hopsworks"
  cb_recipe "default"  
  action :get_publickey
end  


