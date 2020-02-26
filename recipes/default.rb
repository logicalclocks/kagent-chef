require 'inifile'
require 'securerandom'

ruby_block "whereis_nvidia-smi" do
  ignore_failure true 
  block do
    Chef::Resource::RubyBlock.send(:include, Chef::Mixin::ShellOut)
    systemctl_path = shell_out("which nvidia-smi").stdout
    node.override['kagent']['nvidia-smi_path'] = systemctl_path.strip
  end
end

sudo "nvidia-smi" do
  users       node["kagent"]["user"]
  commands    lazy {[node['kagent']['nvidia-smi_path']]}
  nopasswd    true
  action      :create
  only_if     { node["install"]["sudoers"]["rules"].casecmp("true") == 0 }
  not_if      { node['kagent']['nvidia-smi_path'].empty? } 
end

['start-agent.sh', 'stop-agent.sh', 'restart-agent.sh', 'get-pid.sh', 'status-service.sh', 
  "gpu-kill.sh", "gpu-killhard.sh"].each do |script|
  Chef::Log.info "Installing #{script}"
  template "#{node["kagent"]["home"]}/bin/#{script}" do
    source "#{script}.erb"
    owner node["kagent"]["user"]
    group node["kagent"]["group"]
    mode 0750
  end
end 

# set_my_hostname
if node["vagrant"] === "true" || node["vagrant"] == true 
    node[:kagent][:default][:private_ips].each_with_index do |ip, index| 
      hostsfile_entry "#{ip}" do
        hostname  "hopsworks#{index}"
        action    :create
        unique    true
      end
    end
end

jupyter_python = "true"
if node.attribute?("jupyter") 
  if node["jupyter"].attribute?("python") 
    jupyter_python = "#{node['jupyter']['python']}".downcase
  end
end

template "#{node["kagent"]["home"]}/bin/anaconda_sync.sh" do
  source "anaconda_sync.sh.erb"
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode "750"
  action :create
end

ruby_block "whereis_systemctl" do
  block do
    Chef::Resource::RubyBlock.send(:include, Chef::Mixin::ShellOut)
    systemctl_path = shell_out("which systemctl").stdout
    node.override['kagent']['systemctl_path'] = systemctl_path.strip
  end
end

sudo "kagent_systemctl" do
  users    node["kagent"]["user"]
  commands lazy {["start", "stop", "restart"].map{|command| "#{node['kagent']['systemctl_path']} #{command} *"}}
  nopasswd true
  action   :create
  only_if     { node["install"]["sudoers"]["rules"].casecmp("true") == 0 }
end

kagent_sudoers "anaconda_env" do 
  script_name "anaconda_env.sh"
  template    "anaconda_env.sh.erb"
  user        node["kagent"]["user"]
  group       node["conda"]["group"]
  run_as      node["conda"]["user"]
  variables({
        :jupyter_python => jupyter_python
  })
end

kagent_sudoers "conda" do
    script_name "conda.sh"
    template    "conda.sh.erb"
    user        node["kagent"]["user"]
    group       node["conda"]["group"]
    run_as      node["conda"]["user"]
end

kagent_sudoers "run_csr" do
    script_name "run_csr.sh"
    template    "run_csr.sh.erb"
    user        node["kagent"]["user"]
    group       node["kagent"]["certs_group"]
    run_as      node["kagent"]["certs_user"]
end

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


if !node['install']['cloud'].empty? 
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

deps = ""
if exists_local("hopsworks","default")
  deps = "glassfish-domain1.service"
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
    variables({
              :deps => deps
              })
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
  
  if node['kagent']['enabled'].casecmp? "true"
    kagent_config service_name do
      service "kagent"
      config_file "#{node["kagent"]["etc"]}/config.ini"
      log_file "#{node["kagent"]["dir"]}/logs/agent.log"
      restart_agent false
    end
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

## We can't add Consul dependency in kagent, it leads to cyclic dep
consul_domain = "consul"
if node.attribute?('consul') && node['consul'].attribute?('domain')
  consul_domain = node['consul']['domain']
end

hopsworks_port = "8181"
if node.attribute? "hopsworks"
  if node["hopsworks"].attribute? "https" and node["hopsworks"]["https"].attribute? "port"
    hopsworks_port = node["hopsworks"]["https"]["port"]
  end
end

dashboard_endpoint = "hopsworks.glassfish.service.#{consul_domain}:#{hopsworks_port}"

# Default to hostname found in /etc/hosts, but allow user to override it.
# First with DNS. Highest priority if user supplies the actual hostname

if node['install']['cloud'].eql? "azure"
  my_ip = my_private_ip()
  hostname = resolve_hostname(my_ip)
else
  hostname = node['fqdn']
end

if node['install']['localhost'].casecmp?("true")
  hostname = "localhost"
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

## blacklisted_envs is a comma separated list of Anaconda environments
## that should not be deleted by Conda GC
# python envs
blacklisted_envs = node['kagent']['python_conda_versions'].split(",").map(&:strip)
                     .map {|p| p.gsub(".", "") }.map {|p| "python" + p}.join(",")
# hops-system anaconda env
blacklisted_envs += ",hops-system,airflow"

# environment used by Hopsworks Cloud
unless node['install']['cloud'].strip.empty?
  blacklisted_envs += ",cloud"
end

template "#{node["kagent"]["etc"]}/config.ini" do
  source "config.ini.erb"
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode 0640
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

# For upgrades we need to CHOWN the directory and the files underneat to certs:certs
bash "chown_#{node['kagent']['certs_dir']}" do
  code <<-EOH
    chown -R #{node['kagent']['certs_user']}:#{node['kagent']['certs_group']} #{node['kagent']['certs_dir']}
  EOH
  action :run
  only_if { ::Dir.exists?(node['kagent']['certs_dir'])}
end

bash "chown_#{node['kagent']['certs_dir']}" do
  code <<-EOH
    chown #{node['kagent']['certs_user']}:#{node['kagent']['certs_group']} #{node['kagent']['etc']}/state_store/crypto_material_state.pkl
  EOH
  action :run
  only_if { ::File.exists?("#{node['kagent']['etc']}/state_store/crypto_material_state.pkl")}
end



template "#{node["kagent"]["certs_dir"]}/keystore.sh" do
  source "keystore.sh.erb"
  owner node["kagent"]["certs_user"]
  group node["kagent"]["certs_group"]
  mode 0700
  variables({:fqdn => hostname})
end

if node["kagent"]["test"] == false && (not conda_helpers.is_upgrade)
  hopsworks_alt_url = "https://#{private_recipe_ip("hopsworks","default")}:8181" 
  if node.attribute? "hopsworks"
    if node["hopsworks"].attribute? "https" and node["hopsworks"]['https'].attribute? ('port')
      hopsworks_alt_url = "https://#{private_recipe_ip("hopsworks","default")}:#{node['hopsworks']['https']['port']}"
    end
  end
  kagent_keys "sign-certs" do
    hopsworks_alt_url hopsworks_alt_url
    action :csr
  end
end

kagent_keys "combine_certs" do 
  action :combine_certs
end 

bash "convert private key to PKCS#1 format on update" do
  user "root"
  group node['kagent']['certs_group']
  code <<-EOH                                                                                                       
       openssl rsa -in #{node['kagent']['certs_dir']}/priv.key -out #{node['kagent']['certs_dir']}/priv.key.rsa
       chmod 640 #{node['kagent']['certs_dir']}/priv.key.rsa
       chown #{node['kagent']['certs_user']}:#{node['kagent']['certs_group']} #{node['kagent']['certs_dir']}/priv.key.rsa
  EOH
  only_if { conda_helpers.is_upgrade and File.exists?("#{node['kagent']['certs_dir']}/priv.key")}
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
