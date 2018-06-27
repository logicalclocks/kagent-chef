# ubuntu python-mysqldb package install only works if we first run "apt-get update; apt-get upgrade"

case node["platform_family"]
when "debian"
  bash "apt_update_install_build_tools" do
    user "root"
    code <<-EOF
   apt-get update -y 
   apt-get install build-essential -y 
   apt-get install libssl-dev -y 
   apt-get install jq -y 
 EOF
  end

# Change lograte policy
  cookbook_file '/etc/logrotate.d/rsyslog' do
    source 'rsyslog.ubuntu'
    owner 'root'
    group 'root'
    mode '0644'
  end

  package "python2.7" 
  package "python-pip" 
  package "python2.7-dev" 
  package "python2.7-lxml" 
  package "python-openssl"

when "rhel"
  package "epel-release"

# gcc, gcc-c++, kernel-devel are the equivalent of "build-essential" from apt.
  package "gcc"
  package "gcc-c++"
  package "kernel-devel" 
  package "openssl"
  package "openssl-devel"
  package "openssl-libs" 
  package "python" 
  package "python-pip" 
  package "python-devel" 
  package "python-lxml" 
  package "jq" 
  package "pyOpenSSL"
  # Change lograte policy
  cookbook_file '/etc/logrotate.d/syslog' do
    source 'syslog.centos'
    owner 'root'
    group 'root'
    mode '0644'
  end
end


#installs python 2
# include_recipe "poise-python"
# The openssl::upgrade recipe doesn't install openssl-dev/libssl-dev, needed by python-ssl
# Now using packages in ubuntu/centos.
#include_recipe "openssl::upgrade"

group node["kagent"]["group"] do
  action :create
  not_if "getent group #{node["kagent"]["group"]}"
end

group node["kagent"]["certs_group"] do
  action :create
  not_if "getent group #{node["kagent"]["certs_group"]}"
end

user node["kagent"]["user"] do
  gid node["kagent"]["group"]
  manage_home true
  home "/home/#{node["kagent"]["user"]}"
  action :create
  shell "/bin/bash"
  not_if "getent passwd #{node["kagent"]["user"]}"
end

group node["kagent"]["group"] do
  action :modify
  members ["#{node["kagent"]["user"]}"]
  append true
end

group node["kagent"]["certs_group"] do
  action :modify
  members ["#{node["kagent"]["user"]}"]
  append true
end


# ubuntu python-mysqldb package install only works if we first run "apt-get update; apt-get upgrade"
if platform?("ubuntu", "debian") 
  package "python-mysqldb" do
   options "--force-yes"
   action :install
  end
elsif platform?("centos","redhat","fedora")
  package "MySQL-python" do
    action :install
  end
else
  Chef::Log.warn "Needs to install python mysql libs - this Linux distribution is not supported. Only debian/ubuntu and rhel/centos supported."
end

bash "install_python" do
  user 'root'
  ignore_failure true
  code <<-EOF
  pip install --upgrade inifile
  pip install --upgrade requests
  pip install --upgrade bottle
  pip install --upgrade CherryPy
  pip install --upgrade pyOpenSSL
  pip install --upgrade netifaces
  pip install --upgrade IPy
  pip install --upgrade pexpect
  pip install --upgrade wsgiserver
 EOF
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
  action :create
  not_if { File.directory?("#{node["kagent"]["dir"]}") }
end

directory node["kagent"]["home"] do
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode "750"
  action :create
end

directory node["kagent"]["certs_dir"] do
  owner node["kagent"]["user"]
  group node["kagent"]["certs_group"]
  mode "750"
  action :create
end

if node["kagent"]["test"] == false && node['install']['upgrade'] == "true"
  bash "copy_old_config_ini_to_new_version" do
    user "root"
    code <<-EOF
      cp -p #{node["kagent"]["base_dir"]}/config.ini #{node["kagent"]["home"]}
 EOF
  end
end

link node["kagent"]["base_dir"] do
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  to node["kagent"]["home"]
end

directory "#{node["kagent"]["base_dir"]}/bin" do
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode "755"
  action :create
end

directory node["kagent"]["keystore_dir"] do
  owner "root"
  group node["kagent"]["certs_group"]
  mode "750"
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

remote_directory "#{node["kagent"]["base_dir"]}/kagent_utils" do
  source 'kagent_utils'
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode 0710
  files_owner node["kagent"]["user"]
  files_group node["kagent"]["group"]
  files_mode 0710
  notifies :run, 'bash[install-kagent_utils]', :immediately
end

bash "install-kagent_utils" do
  user "root"
  code <<-EOH
       cd #{node["kagent"]["base_dir"]}/kagent_utils
       pip install -U .
  EOH
end

cookbook_file "#{node["kagent"]["base_dir"]}/agent.py" do
  source 'agent.py'
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode 0710
end

## Touch cssr script log file as kagent user, so agent.py can write to it
file "#{node["kagent"]["base_dir"]}/csr.log" do
  mode '0750'
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  action :touch
end

cookbook_file "#{node["kagent"]["certs_dir"]}/csr.py" do
  source 'csr.py'
  owner node["kagent"]["user"]
  group node["kagent"]["certs_group"]
  mode 0710
end

['start-agent.sh', 'stop-agent.sh', 'restart-agent.sh', 'get-pid.sh'].each do |script|
  Chef::Log.info "Installing #{script}"
  template "#{node["kagent"]["base_dir"]}/bin/#{script}" do
    source "#{script}.erb"
    owner node["kagent"]["user"]
    group node["kagent"]["group"]
    mode 0750
  end
end 

['services'].each do |conf|
  Chef::Log.info "Installing #{conf}"
  template "#{node["kagent"]["base_dir"]}/#{conf}" do
    source "#{conf}.erb"
    owner node["kagent"]["user"]
    group node["kagent"]["group"]
    mode 0644
    action :create_if_missing
  end
end

['start-service.sh', 'stop-service.sh', 'restart-service.sh', 'status-service.sh'].each do |script|
  template  "#{node["kagent"]["base_dir"]}/bin/#{script}" do
    source "#{script}.erb"
    owner "root"
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

hadoop_version = "2.8.2.3"
if node.attribute?("hops") 
  if node["hops"].attribute?("version") 
    hadoop_version = node['hops']['version']
  end
end


template "#{node["kagent"]["home"]}/bin/conda.sh" do
  source "conda.sh.erb"
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode "750"
  action :create
end

template "#{node["kagent"]["home"]}/bin/anaconda_env.sh" do
  source "anaconda_env.sh.erb"
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode "750"
  action :create
  variables({
        :jupyter_python => jupyter_python
#        :hadoop_version => hadoop_version
  })
end


template "/etc/sudoers.d/kagent" do
  source "sudoers.erb"
  owner "root"
  group "root"
  mode "0440"
  variables({
                :user => node["kagent"]["user"],
                :conda =>  "#{node["kagent"]["base_dir"]}/bin/conda.sh",
                :anaconda =>  "#{node["kagent"]["base_dir"]}/bin/anaconda_env.sh",
                :start => "#{node["kagent"]["base_dir"]}/bin/start-service.sh",
                :stop => "#{node["kagent"]["base_dir"]}/bin/stop-service.sh",
                :restart => "#{node["kagent"]["base_dir"]}/bin/restart-service.sh",
                :status => "#{node["kagent"]["base_dir"]}/bin/status-service.sh",
                :startall => "#{node["kagent"]["base_dir"]}/bin/start-all-local-services.sh",
                :stopall => "#{node["kagent"]["base_dir"]}/bin/shutdown-all-local-services.sh",
                :statusall => "#{node["kagent"]["base_dir"]}/bin/status-all-local-services.sh",
                :rotate_service_key => "#{node[:kagent][:certs_dir]}/csr.py"
              })
  action :create
end  


include_recipe "kagent::anaconda"
