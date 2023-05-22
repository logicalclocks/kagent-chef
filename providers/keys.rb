action :append2ChefTrustAnchors do
  crypto_dir = x509_helper.get_crypto_dir(node['kagent']['user'])
  bash "append hops ca certificates to chef cacerts" do
    user "root" 
    group "root" 
    code <<-EOH
      set -eo pipefail
      echo "Hops Root CA " >>  /opt/chefdk/embedded/ssl/certs/cacert.pem
      echo "==================" >>  /opt/chefdk/embedded/ssl/certs/cacert.pem
      cat #{crypto_dir}/#{node['x509']['ca']['root']} >> /opt/chefdk/embedded/ssl/certs/cacert.pem

      echo "Hops Intermediate CA " >>  /opt/chefdk/embedded/ssl/certs/cacert.pem
      echo "==================" >>  /opt/chefdk/embedded/ssl/certs/cacert.pem
      cat #{crypto_dir}/#{node['x509']['ca']['intermediate']} >> /opt/chefdk/embedded/ssl/certs/cacert.pem
    EOH
    only_if { ::File.exists?( "/opt/chefdk/embedded/ssl/certs/cacert.pem" ) }
  end
end 

action :generate do
  homedir = "#{new_resource.homedir}"
  cb_user = "#{new_resource.cb_user}"
  cb_group = "#{new_resource.cb_group}"

  bash "generate-ssh-keypair-for-#{homedir}" do
    user cb_user
    group cb_group
    code <<-EOF
     ssh-keygen -f #{homedir}/.ssh/id_ed25519 -t ed25519 -q -N ''
  EOF
    not_if { node['install']['dev_ssh_keys'].casecmp?('false') || ::File.exists?( "#{homedir}/.ssh/id_ed25519" ) }
  end
end



#
# Add this code in the cookbook/recipe that is returning its public key - to be added to the
# authorized_keys of another user
#
action :return_publickey do
  homedir = "#{new_resource.homedir}"
  contents = ''
  cb = "#{new_resource.cb_name}"
  recipeName = "#{new_resource.cb_recipe}"
  cb_user = "#{new_resource.cb_user}"
  cb_group = "#{new_resource.cb_group}"
  recipeName = "#{new_resource.cb_recipe}"
  if node['install']['dev_ssh_keys'].casecmp?('true')
    contents = ::IO.read("#{homedir}/.ssh/id_ed25519.pub")
    raise if contents.empty?
    Chef::Log.info "Public key read is: #{contents}"
  end
 
  node.default["#{cb}"]["#{recipeName}"][:public_key] = contents
  template "#{homedir}/.ssh/config" do
    source "ssh_config.erb" 
    owner cb_user
    group cb_group
    mode 0600
    cookbook "kagent"
    action :create_if_missing
    not_if { node['install']['dev_ssh_keys'].casecmp?('false') }
  end
 
  kagent_param "/tmp" do
    executing_cookbook cb
    executing_recipe  recipeName
    cookbook cb
    recipe recipeName
    param "public_key"
    value  "#{contents}"
    not_if { node['install']['dev_ssh_keys'].casecmp?('false') }
  end
end

#
# Add this LWRP in the recipe of a user that wants to add the public_key (id_ed25519.pub) of an
# upstream user to its authorized_keys file
#
action :get_publickey do
  homedir = "#{new_resource.homedir}"
  cb = "#{new_resource.cb_name}" 
  recipeName = "#{new_resource.cb_recipe}"
  cb_user = "#{new_resource.cb_user}"
  cb_group = "#{new_resource.cb_group}"

  key_contents = node["#{cb}"]["#{recipeName}"][:public_key]
  Chef::Log.debug "Public key read is: #{key_contents}"
  bash "add_#{cb}_#{recipeName}_public_key" do
    user "root"
    code <<-EOF
      set -e
      if [ ! -d #{homedir}/.ssh ] ; then
        mkdir #{homedir}/.ssh
      fi
      chmod 700 #{homedir}/.ssh
      echo "#{key_contents}" >> #{homedir}/.ssh/authorized_keys
      chmod 600 #{homedir}/.ssh/authorized_keys
      chown -R #{cb_user}:#{cb_group} #{homedir}/.ssh
  EOF
     not_if "grep #{key_contents} #{homedir}/.ssh/authorized_keys"
     not_if { node['install']['dev_ssh_keys'].casecmp?('false') }
  end
end
