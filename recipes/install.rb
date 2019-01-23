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
  package "python2.7-dev"
  # Needed by pip install MySQL-python
  package "libmysqlclient-dev"

when "rhel"

  if node['rhel']['epel']
    package "epel-release"
  end

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
  package "jq"
  # MySQL-python needs libmysqlclient which in Centos is provided by mariadb-devel
  package "mariadb-devel"
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
  action :create
  manage_home true
  home "/home/#{node['kagent']['user']}"
  shell "/bin/bash"
  system true
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
  mode "700"
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
  owner node["kagent"]["user"]
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

## Touch cssr script log file as kagent user, so agent.py can write to it
file "#{node["kagent"]["dir"]}/csr.log" do
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

template "#{node["kagent"]["certs_dir"]}/run_csr.sh" do
  source 'run_csr.sh.erb'
  owner node['kagent']['user']
  group node['kagent']['group']
  mode 0710
end

['start-agent.sh', 'stop-agent.sh', 'restart-agent.sh', 'get-pid.sh'].each do |script|
  Chef::Log.info "Installing #{script}"
  template "#{node["kagent"]["home"]}/bin/#{script}" do
    source "#{script}.erb"
    owner node["kagent"]["user"]
    group node["kagent"]["group"]
    mode 0750
  end
end 

['start-service.sh', 'stop-service.sh', 'restart-service.sh', 'status-service.sh', 'gpu-kill.sh', 'gpu-killhard.sh'].each do |script|
  template  "#{node["kagent"]["home"]}/bin/#{script}" do
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

template "#{node["kagent"]["home"]}/bin/anaconda_sync.sh" do
  source "anaconda_sync.sh.erb"
  owner node["kagent"]["user"]
  group node["kagent"]["group"]
  mode "750"
  action :create
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
                :rotate_service_key => "#{node[:kagent][:certs_dir]}/run_csr.sh",
                :gpu_kill => "#{node["kagent"]["base_dir"]}/bin/gpu-kill.sh",
                :gpu_killhard => "#{node["kagent"]["base_dir"]}/bin/gpu-killhard.sh"
              })
  action :create
end  
