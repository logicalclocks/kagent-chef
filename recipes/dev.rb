private_ip = my_private_ip()

# This is a development recipe, used together with virtualbox. All our boxes in the 
# 3 vm setup, have IPs starting with 192.168

# `ifconfig | grep -B 1 '192.168' | awk '{split($0,a," "); print a[1];}' | head -1`
pub_net_if = ""
ruby_block 'discover_public_interface' do
  block do
    Chef::Resource::RubyBlock.send(:include, Chef::Mixin::ShellOut)
    command = "ifconfig | grep -B 1 '192.168' | awk '{split($0,a,\" \"); print a[1];}' | head -1"
    pub_net_if = shell_out(command).stdout.gsub(/\n/, '').gsub(/:/, '')
  end
end

priv_net_if = ""
ruby_block 'discover_private_interface' do
  block do
    Chef::Resource::RubyBlock.send(:include, Chef::Mixin::ShellOut)
    command = "ifconfig | grep -B 1 '10.0.2.15' | awk '{split($0,a,\" \"); print a[1];}' | head -1"
    priv_net_if = shell_out(command).stdout.gsub(/\n/, '').gsub(/:/, '')
  end
end

directory '/etc/iptables' do
  owner 'root'
  group 'root'
  recursive true
  action :delete
end

directory '/etc/iptables' do
  owner 'root'
  group 'root'
  mode '0700'
  action :create
end

template '/etc/iptables/iptables.rules' do
  source 'iptables.rules.erb'
  owner 'root'
  group 'root'
  mode '0700'
  variables( lazy {
    h = {}
    h[:pub_net_if] = pub_net_if
    h[:priv_net_if] = priv_net_if
    h[:private_ip] = private_ip
    h[:public_ip] = "10.0.2.15"
    h
  })
  notifies :run, 'execute[ip_forward]', :immediately
end

execute 'ip_forward' do
  command "sed -i '/^#net.ipv4.ip_forward*/s/^#//' /etc/sysctl.conf"
  user 'root'
  group 'root'
  action :nothing
  notifies :run , 'execute[ip_tables]', :immediately
end

execute 'ip_tables' do
  command "iptables-restore < /etc/iptables/iptables.rules"
  user 'root'
  group 'root'
  action :nothing
end
