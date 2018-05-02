service_name = "kagent"

agent_password = ""
if node["kagent"]["password"].empty? == false
 agent_password = "password = #{node["kagent"]["password"]}"
end

case node[:platform]
when "ubuntu"
 if node[:platform_version].to_f <= 14.04
   node.default["systemd"] = "false"
 end
end

#
# Hack because of a problem with Cheroot 
#
bash "reinstall_backports_functools" do
  user 'root'
  ignore_failure true
  code <<-EOF
  yes | pip uninstall backports.functools_lru_cache
  yes | pip install backports.functools_lru_cache
 EOF
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

dashboard_endpoint = "10.0.2.15"  + ":" + node["kagent"]["dashboard"]["port"]

if node.attribute? "hopsworks"
  begin
    if node["hopsworks"].attribute? "port"
      dashboard_endpoint = private_recipe_ip("hopsworks","default")  + ":" + node["hopsworks"]["port"]
    else
      dashboard_endpoint = private_recipe_ip("hopsworks","default")  + ":" + node["kagent"]["dashboard"]["port"]
    end
  rescue
    dashboard_endpoint =
    Chef::Log.warn "could not find the hopsworks server ip to register kagent to!"
  end
end

network_if = node["kagent"]["network"]["interface"]

# If the network i/f name not set by the user, set default values for ubuntu and centos
if network_if == ""
  case node["platform_family"]
  when "debian"
    network_if = "eth0"
  when "rhel"
    network_if = "enp0s3"
  end
end


template "#{node["kagent"]["base_dir"]}/bin/start-all-local-services.sh" do
  source "start-all-local-services.sh.erb"
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode 0740
end


template "#{node["kagent"]["base_dir"]}/bin/shutdown-all-local-services.sh" do
  source "shutdown-all-local-services.sh.erb"
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode 0740
end

template "#{node["kagent"]["base_dir"]}/bin/status-all-local-services.sh" do
  source "status-all-local-services.sh.erb"
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode 0740
end


#
# Certificate Signing code - Needs Hopsworks dashboard
#


template "#{node["kagent"]["base_dir"]}/keystore.sh" do
  source "keystore.sh.erb"
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode 0700
   variables({
              :directory => node["kagent"]["keystore_dir"],
              :keystorepass => node["hopsworks"]["master"]["password"]
            })
end

# Default to hostname found in /etc/hosts, but allow user to override it.
# First with DNS. Highest priority if user supplies the actual hostname
hostname = node['hostname']  
if node['kagent']['dns'].eql? "true"
  hostname = node['fqdn']
end

if private_ip.eql? "127.0.0.1"
  hostname="localhost"
end  

if node["kagent"].attribute?("hostname")
   if node["kagent"]["hostname"].empty? == false
      hostname = node["kagent"]["hostname"]
   end
end

Chef::Log.info "Hostname to register kagent in config.ini is: #{hostname}"
if hostname.empty?
  raise "Hostname in kagent/config.ini cannot be empty"
end


hops_dir=node['install']['dir']
if node.attribute?("hops") && node["hops"].attribute?("dir") 
  hops_dir=node['hops']['dir'] + "/hadoop"
end
if hops_dir == "" 
 # Guess that it is the default value
 hops_dir = node['install']['dir'] + "/hadoop"
end



#
# use :create_if_missing, as if there is a failure during/after the csr.py program,
# you will get a failure. csr.py adds a password entry to the [agent] section. 
# The file will be created without the agent->pasword if it is re-run and the password will be lost. 
#
template "#{node["kagent"]["base_dir"]}/config.ini" do
  source "config.ini.erb"
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode 0600
  action :create_if_missing
  variables({
              :rest_url => "http://#{dashboard_endpoint}/",
              :rack => '/default',
              :hostname => hostname,
              :public_ip => public_ip,
              :private_ip => private_ip,
              :network_if => network_if,
              :hops_dir => hops_dir,
              :agent_password => agent_password
            })
if node["services"]["enabled"] == "true"  
  notifies :enable, "service[#{service_name}]"
end
  notifies :restart, "service[#{service_name}]", :delayed
end

if node["kagent"]["test"] == false 
    kagent_keys "sign-certs" do
       action :csr
    end
end


execute "rm -f #{node["kagent"]["pid_file"]}"

case node['platform_family']
when "rhel"
  # bash "disable-iptables" do
  #   code <<-EOH
  #   service iptables stop
  # EOH
  #   only_if "test -f /etc/init.d/iptables && service iptables status"
  # end
  
end

if node["kagent"]["allow_ssh_access"] == 'true'
  homedir = "/home/#{node["kagent"]["user"]}"
  kagent_keys "#{homedir}" do
    cb_user "#{node["kagent"]["user"]}"
    cb_group "#{node["kagent"]["group"]}"
    cb_name "hopsworks"
    cb_recipe "default"  
    action :get_publickey
  end  
end



if node["kagent"]["cleanup_downloads"] == 'true'

  file "/tmp/#{d}*.tgz" do
    action :delete
    ignore_failure true
  end

end

if node["install"]["addhost"] == 'true'

 bash "sync-anaconda-with-existing-cluster" do
   user "root"
   code <<-EOH
     #{node['kagent']['base_dir']}/bin/anaconda_sync.sh
   EOH
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


