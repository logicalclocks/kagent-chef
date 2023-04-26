action :register_host do
    hopsworks_alt_url = ""
    unless new_resource.hopsworks_alt_url.nil?
        hopsworks_alt_url = "--alt-url #{new_resource.hopsworks_alt_url}"
    end
    bash "Register Host with Hopsworks" do
        user node['kagent']['certs_user']
        group node['kagent']['group']
        code <<-EOH
            #{node["kagent"]["certs_dir"]}/hopsify --config #{node['kagent']['etc']}/config.ini #{hopsworks_alt_url} host
        EOH
    end
end

action :create_user_directory do
    if new_resource.user.nil? || new_resource.crypto_directory.nil?
        raise "User/Crypto directory are required to generate X509"
    end

    directory new_resource.crypto_directory do
        owner node['kagent']['certs_user']
        group node['kagent']['certs_group']
        mode '0750'
        action :create
        notifies :run, 'bash[apply-acl]', :immediately
    end

    bash "apply-acl" do
        user "root"
        group "root"
        code <<-EOH
            set -e
            setfacl -m u:#{new_resource.user}:rx #{new_resource.crypto_directory}
        EOH
        action :nothing
    end
end

action :generate_x509 do
    kagent_hopsify 'Generate user directory' do
        user new_resource.user
        crypto_directory new_resource.crypto_directory
        action :create_user_directory
    end

    if new_resource.password.nil?
        keystoresPassword = node["hopsworks"]["master"]["password"]
    else
        keystoresPassword = new_resource.password
    end

    hopsworks_alt_url = ""
    unless new_resource.hopsworks_alt_url.nil?
        hopsworks_alt_url = "--alt-url #{new_resource.hopsworks_alt_url}"
    end

    common_name = ""
    unless new_resource.common_name.nil?
        common_name = "--common-name #{new_resource.common_name}"
    end

    bash "Generate Hops TLS x.509 for user #{new_resource.user}" do
        user "root"
        group "root"
        environment 'HOPSIFY_PASSWORD' => keystoresPassword
        code <<-EOH
            set -e
            #{node["kagent"]["certs_dir"]}/hopsify --config #{node['kagent']['etc']}/config.ini x509 #{hopsworks_alt_url} --username #{new_resource.user} #{common_name}
            chmod 750 #{node['kagent']['etc']}/state_store/*
            chown #{node['kagent']['certs_user']}:#{node['kagent']['group']} #{node['kagent']['etc']}/state_store/*
        EOH
        not_if { ::File.exist?("#{new_resource.crypto_directory}/#{x509_helper.get_private_key_pkcs8_name(new_resource.user)}")}
    end

    bash "Renew Hops TLS x.509 for user #{new_resource.user} with SAN" do
        user "root"
        group "root"
        environment 'HOPSIFY_PASSWORD' => keystoresPassword
        code <<-EOH
            set -e
            #{node["kagent"]["certs_dir"]}/hopsify --config #{node['kagent']['etc']}/config.ini x509 #{hopsworks_alt_url} --rotation --username #{new_resource.user} #{common_name}
        EOH
        only_if { conda_helpers.is_upgrade }
        only_if { Gem::Version.new(node['install']['current_version']) <= Gem::Version.new('3.2.0')}
    end
end