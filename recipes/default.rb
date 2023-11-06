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

kagent_sudoers "run_csr" do
    script_name "run_csr.sh"
    template    "run_csr.sh.erb"
    user        node["kagent"]["user"]
    group       node["kagent"]["certs_group"]
    run_as      node["kagent"]["certs_user"]
end

kagent_sudoers "dockerImageDelete" do
  user          node['kagent']['user']
  group         "root"
  script_name   "dockerImageDelete.sh"
  template      "dockerImageDelete.sh.erb"
  run_as        "ALL" # run this as root - inside we change to different users
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

private_ip = my_private_ip()
public_ip = my_public_ip()

## We can't add Consul dependency in kagent, it leads to cyclic dep
consul_region = ""
if node.attribute?("consul") &&
    node["consul"].attribute?("use_datacenter") &&
    node["consul"]["use_datacenter"].casecmp?("true")

  consul_region = "lc"
  if node.attribute?("consul") &&
    node["consul"].attribute?("datacenter")
    consul_region = node['consul']['datacenter']
  end
end

consul_domain = "consul"
if node.attribute?('consul') && node['consul'].attribute?('domain')
  consul_domain = node['consul']['domain']
end

consul_domain_without_region = consul_domain

if !consul_region.eql?("")
  consul_domain = "#{consul_region}.#{consul_domain}"
end

hopsworks_port = "8182"
if node.attribute? "hopsworks"
  if node["hopsworks"].attribute? "internal" and node["hopsworks"]["internal"].attribute? "port"
    hopsworks_port = node["hopsworks"]["internal"]["port"]
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
              :region => consul_region
            })
end

# For upgrades we need to CHOWN the directory and the files underneat to certs:certs
bash "chown_#{node['kagent']['certs_dir']}" do
  code <<-EOH
    chown -R #{node['kagent']['certs_user']}:#{node['kagent']['certs_group']} #{node['kagent']['certs_dir']}
  EOH
  action :run
  only_if { ::Dir.exists?(node['kagent']['certs_dir'])}
end

template "#{node["kagent"]["certs_dir"]}/keystore.sh" do
  source "keystore.sh.erb"
  owner node["kagent"]["certs_user"]
  group node["kagent"]["certs_group"]
  mode 0700
  variables({:fqdn => hostname})
end

if node["kagent"]["enabled"].casecmp?("true")
  hopsworks_alt_url = "https://#{private_recipe_ip("hopsworks","default")}:#{hopsworks_port}"

  kagent_hopsify "Register Host" do
    hopsworks_alt_url hopsworks_alt_url
    action :register_host
  end

  kagent_hopsify "Generate x.509" do
    user node['kagent']['user']
    crypto_directory x509_helper.get_crypto_dir(node['kagent']['user'])
    hopsworks_alt_url hopsworks_alt_url
    action :generate_x509
  end

  begin
    registry_ip = private_recipe_ip("hops","docker_registry")
    registry_host = resolve_hostname(registry_ip)
  rescue
    registry_host = "localhost"
    Chef::Log.warn "could not find the docker registry ip!"
  end

  #for docker to push and pull from the registry it needs to trust hops_ca.pem
  case node['platform_family']
  when 'rhel'
    cert_target = "/etc/pki/ca-trust/source/anchors/#{registry_host}.crt"
    update_command = "update-ca-trust"
  when 'debian'
    cert_target = "/usr/local/share/ca-certificates/#{registry_host}.crt"
    update_command = "update-ca-certificates"
  end

  bash 'remove-system-trust-cert' do
    user 'root'
    code <<-EOH
      set -e
      rm -f #{cert_target}
      #{update_command}
    EOH
    only_if { ::File.exist?(cert_target) }
  end

  kagent_crypto_dir = x509_helper.get_crypto_dir(node['kagent']['user'])
  hops_ca_bundle = "#{kagent_crypto_dir}/#{x509_helper.get_hops_ca_bundle_name()}"
  registry_port = 4443
  if (node.attribute?("hops") && node["hops"].attribute?("docker") && 
      node["hops"]["docker"].attribute?("registry") && node["hops"]["docker"]["registry"].attribute?("port"))
    registry_port = node['hops']['docker']['registry']['port']
  end

  registry_domains = []
  if node['install']['regions']['primary'].empty? && node['install']['regions']['secondary'].empty?
    registry_domains.push("registry.service.#{consul_domain}")
  else
    registry_domains.push("registry.service.#{node['install']['regions']['primary']}.#{consul_domain_without_region}")
    registry_domains.push("registry.service.#{node['install']['regions']['secondary']}.#{consul_domain_without_region}")
  end

  for registry_domain in registry_domains do
    directory "/etc/docker/certs.d/#{registry_domain}:#{registry_port}" do
      owner 'root'
      group 'root'
      mode '0755'
      recursive true
    end

    link "/etc/docker/certs.d/#{registry_domain}:#{registry_port}/ca.crt" do
      owner 'root'
      group 'root'
      mode '0755'
      to hops_ca_bundle
    end
  end

  if exists_local("hopsworks", "default")
    hopsworks_user = "glassfish"
    if node.attribute?("hopsworks")
      if node['hopsworks'].attribute?("user")
        hopsworks_user = node['hopsworks']['user']
      end
    end
    # Generate glassfish user certificates here
    # Cannot do it in hopsworks::default as hopsify is not setup yet
    kagent_hopsify "Generate x.509" do
      user hopsworks_user
      crypto_directory x509_helper.get_crypto_dir(hopsworks_user)
      hopsworks_alt_url hopsworks_alt_url
      common_name node['fqdn']
      action :generate_x509
    end
  end

  kagent_keys "combine_certs" do 
    crypto_dir kagent_crypto_dir
    action :append2ChefTrustAnchors
  end
else
  # Create just the user directory without generating the certificates
  # It is needed when joining managed NDB nodes in Hopsworks cluster
  kagent_hopsify "Create user x.509 directory" do
    user node['kagent']['user']
    crypto_directory x509_helper.get_crypto_dir(node['kagent']['user'])
    action :create_user_directory
  end
end

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

deps = ""
if exists_local("hopsworks","default")
  deps = "glassfish-domain1.service"
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

kagent_config service_name do
  action :systemd_reload
end
  
kagent_config service_name do
  service "kagent"
  
  config_file "#{node["kagent"]["etc"]}/config.ini"
  log_file "#{node["kagent"]["logs"]}/agent.log"
  restart_agent false
  only_if { node['kagent']['enabled'].casecmp? "true" }
end

homedir = node['kagent']['user'].eql?("root") ? "/root" : conda_helpers.get_user_home(node['kagent']['user'])
kagent_keys "#{homedir}" do
  cb_user "#{node['kagent']['user']}"
  cb_group "#{node['kagent']['group']}"
  cb_name "hopsworks"
  cb_recipe "default"  
  action :get_publickey
  only_if { node['kagent']['enabled'].casecmp? "true" }
end  
