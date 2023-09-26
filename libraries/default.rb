require 'resolv'

# http://serverfault.com/questions/331936/setting-the-hostname-fqdn-or-short-name
# http://hardoop.blogspot.se/2013/02/hadoop-and-fqdn.html
# https://github.com/caskdata/hadoop_cookbook/blob/master/libraries/helpers.rb
# hostname -fqdn   is used by the tasktracker

module Kagent
  module Helpers
# If the public-ip is empty, return a private-ip instead
    def my_public_ip()
      if node.attribute?("public_ips") == false || node["public_ips"].empty?
         Chef::Log.error "Could not find a public_ip for this host"
         raise ArgumentError, "No public_ip found", node['host']
      end
      return node["public_ips"][0]
    end

    def my_dns_name()
      node["public_ips"][0]
      return dns_lookup(ip)
    end
    
    def my_private_ip()
      if node.attribute?("private_ips") == false || node["private_ips"].empty?
         Chef::Log.error "Could not find a private_ip for this host"
         raise ArgumentError, "No private_ip found", node['host']
      end
      return node["private_ips"][0]
    end

    def my_hostname()
      my_ip = my_private_ip()

      begin
        hostf = Resolv::Hosts.new
        h = hostf.getname("#{my_ip}")
      rescue
        dns = Resolv::DNS.new
        h = dns.getname("#{my_ip}")
      end

      return h
    end

    def my_gateway_ip()
      if node.attribute?("gateway_ips") == false || node["gateway_ips"].empty?
         Chef::Log.error "Could not find a gateway_ip for this host"
         raise ArgumentError, "No gateway_ip found", node['host']
      end
      return node["gateway_ips"][0]
    end


    def valid_cookbook(cookbook)
      if node.attribute?(cookbook) == false
        Chef::Log.error "Invalid cookbook name: #{cookbook}"
        raise ArgumentError, "Invalid Cookbook name", cookbook
      end
    end

    def valid_recipe(cookbook, recipe)
      valid_cookbook(cookbook)
      if node[cookbook].attribute?(recipe) == false
        Chef::Log.error "Invalid cookbook/recipe name: #{cookbook}/#{recipe}"
        raise ArgumentError, "Invalid Recipe fo cookbook #{cookbook}", recipe
      end
    end

    def valid_attribute(cookbook, recipe, attr)
      valid_recipe(cookbook, recipe)
      if node[cookbook][recipe].attribute?(attr) == false
        Chef::Log.error "Invalid cookbook/recipe/attr name: #{cookbook}/#{recipe}/#{attr}"
        raise ArgumentError, "Invalid Attribute for Recipe to cookbook #{cookbook}/#{recipe}", attr
      end
    end

    def public_recipe_ip(cookbook, recipe)
      valid_recipe(cookbook,recipe)
      ip = node[cookbook][recipe][:public_ips][0]
    end

    def private_recipe_ip(cookbook, recipe)
      valid_recipe(cookbook,recipe)
      ip = node[cookbook][recipe][:private_ips][0]
#      if ip.nil? || ip.empty? then
#        Chef::Log.error "No IP found for #{cookbook}/#{recipe}"
#        raise ArgumentError, "No IP found for Recipe to cookbook #{cookbook}/#{recipe}", recipe
#      end
    end


    def exists_local(cookbook, recipe)
      begin
        my_ip = my_private_ip()
        service_ips = private_recipe_ips(cookbook,recipe)

        if service_ips.nil?
          return false
        end

        found = false
        for host in service_ips
          if my_ip.eql? host
            found = true
          end
        end
        return found
      rescue
        return false
      end
    end

    
    def private_recipe_ips(cookbook, recipe)
      valid_recipe(cookbook,recipe)
      return node[cookbook][recipe][:private_ips]
    end

    def resolve_hostname(ip)
      max_attempts = 10
      while true
        begin
          return resolve_hostname_internal(ip)
        rescue StandardError => ex
          max_attempts -= 1
          if max_attempts < 0
            raise ex
          end
          sleep(0.5)
        end
      end
    end

    def resolve_hostname_internal(ip)
      require 'resolv'
      resolver = Resolv.new(resolvers=[Resolv::Hosts.new, Resolv::DNS.new])
      hostnames = resolver.getnames(ip)

      # Hosts in Azure will have 2 hostnames - a global one and a private DNS one.
      if node['install']['cloud'].eql? "azure"
        hostnames = Resolv.getnames(ip)
        # all Azure hosts get this base DNS domain - this is not the private DNS name, exclude it
        hostnames = hostnames.reject { |x| x.include?(".internal.cloudapp.net") }
        # return the last of the hostnames - this is the private DNS Zone hostname in Azure
        hostnames[-1]
      else
        if hostnames.empty?
          raise StandardError.new "Cannot resolve the hostname for IP address: #{ip}"
        end
      	hostnames[0]
      end
    end
    
    def private_recipe_hostnames(cookbook, recipe)
      valid_recipe(cookbook,recipe)
      hostnames = Array.new
      for ip in node[cookbook][recipe][:private_ips]
        # resolve the hostname first in /etc/hosts, then using DNS
        begin
          hostname = resolve_hostname(ip)
        rescue
          if (node["vagrant"])
            hostname = ip
          else
            raise "You need to supply a valid list  of ips for #{cookbook}/#{recipe}"
          end
        end

        hostnames << hostname
      end
      hostnames
    end

    def previous_version()
      node['install']['versions'].split(',')[-1]
    end

    def set_my_hostname()
      my_ip = my_private_ip()
      my_dns_name = my_dns_name()
      hostsfile_entry "#{my_ip}" do
        hostname  node["fqdn"]
        unique    true
        action    :append
      end
    end

    def set_hostnames(cookbook, recipe)
      hostf = Resolv::Hosts.new
      dns = Resolv::DNS.new
      hostnames = Array.new
      for host in node[cookbook][recipe][:private_ips]
        # resolve the hostname first in /etc/hosts, then using DNS
        # If not found, then write an entry for it in /etc/hosts
        begin
          h = dns.getname("#{host}")
        rescue
          # gsub() returns a copy of the modified str with replacements, leaves original string intact.
          # Hostname should not contain '-','_', capital letters
          # http://hortonworks.com/community/forums/topic/not-able-to-start-namenode-via-ambari/
          hostName = host.gsub("\.","")
          h = "#{recipe}#{hostName}"
        end
        hostsfile_entry "#{host}" do
          hostname  "#{h}"
          action    :append
          unique    true
        end

      end

    end

    # lookup fqdn of node using  dns.
    # return ip address if dns fails after 6 seconds
    def dns_lookup ip
      Chef::Log.debug("Resolving IP #{ip}")
      fqdn = ip
      begin
        # set DNS resolution timeout to 6 seconds, otherwise it will take about 80s then throws exception when DNS server is not reachable
        fqdn = Timeout.timeout(6) { Resolv.getname(ip) }
        Chef::Log.info("Resolved IP #{ip} to FQDN #{fqdn}")
      rescue StandardError => e
        Chef::Log.warn("Unable to resolve IP #{ip} to FQDN due to #{e}")
      end
      return fqdn
    end

    # get ndb_mgmd_connectstring, or list of mysqld endpoints
    def service_endpoints(cookbook, recipe, port)
      str = ""
      for n in node[cookbook][recipe][:private_ips]
        str += n + ":" + "#{port}" + ","
      end
      str = str.chop
      str
    end

    def ndb_connectstring()
      connectString = ""
      for n in node["ndb"]["mgmd"]["private_ips"]
        connectString += "#{n}:#{node["ndb"]["mgmd"]["port"]},"
      end
      # Remove the last ','
      connectString = connectString.chop
      node.normal["ndb"]["connectstring"] = connectString
    end

    def get_ee_basic_auth_header()
      # NOTE FOR YOU: Remember to add 'sensitive true' as remote_file property
      username = node['install']['enterprise']['username']
      password = node['install']['enterprise']['password']
      if username.nil? and password.nil?
        return {}
      end
      credentials_b64 = Base64.encode64("#{username}:#{password}").gsub("\n", "")
      header = {}
      header['Authorization'] = "Basic #{credentials_b64}"
      header
    end

    def service_discovery_enabled()
       node['consul']['enabled'].casecmp?("true")
    end

    ## Baking Images for hopsworks.ai
    def is_managed_cloud
      node['install']['enterprise']['install'].casecmp? "true" and exists_local("cloud", "default")
    end

    def http_request_follow_redirect(url, form_params: nil, 
                                     body: nil, authorization: nil, 
                                     contenttype: nil)
      require 'net/https'

      request = Net::HTTP::Post.new(url)
      unless body
        request.set_form_data(form_params, '&')
      else
        request['Content-Type'] = contenttype ? contenttype : "application/json"
        request['Authorization'] = authorization 
        request.body = body
      end

      http = Net::HTTP.new(url.host, url.port)
      http.read_timeout = 120
      http.use_ssl = true
      http.verify_mode = OpenSSL::SSL::VERIFY_NONE

      response = http.request(request)

      if( response.is_a?( Net::HTTPRedirection) )
        return http_request_follow_redirect(URI.parse(response['location']), 
                                            form_params: form_params, body: body, 
                                            authorization: authorization,
                                            contenttype: contenttype)
      end

      return response
    end
  end
end

Chef::Recipe.send(:include, Kagent::Helpers)
Chef::Resource.send(:include, Kagent::Helpers)
Chef::Provider.send(:include, Kagent::Helpers)
