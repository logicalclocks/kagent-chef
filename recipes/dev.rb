private_ip = my_private_ip()

# This is a development recipe, used together with virtualbox. All our boxes in the 
# 3 vm setup, have IPs starting with 192.168
# This recipe is meant to be used in a Vbox development environment  
pub_net_if = ""
priv_net_if = ""
node['network']['interfaces'].each do |iface_name, iface| 
  iface['addresses'].each do |addr, value| 
    if addr.eql?(private_ip)
      pub_net_if = iface_name
    end

    if addr.eql?("10.0.2.15")
      priv_net_if = iface_name
    end
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
  variables({
    'pub_net_if' => pub_net_if,
    'priv_net_if' => priv_net_if,
    'private_ip' => private_ip,
    'public_ip' => "10.0.2.15"
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
