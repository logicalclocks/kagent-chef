require 'uri'
require 'net/http'
require 'json'
require 'open3'

module Kagent
    module JWTHelper
        def get_service_jwt()
            
            hopsworks_hostname = private_recipe_hostnames("hopsworks", "default")[0]
            port = 8181
            if node.attribute?("hopsworks")
                if node['hopsworks'].attribute?("https")
                  if node['hopsworks']['https'].attribute?("port")
                    port = node['hopsworks']['https']['port']
                  end
                end
            end

            url = URI("https://#{hopsworks_hostname}:#{port}/hopsworks-api/api/auth/service")
            
            http = Net::HTTP.new(url.host, url.port)
            # Don't verify the host certificate
            http.use_ssl = true
            http.verify_mode = OpenSSL::SSL::VERIFY_NONE

            request = Net::HTTP::Post.new(url)

            request["Content-Type"] = 'application/x-www-form-urlencoded'
            request.body = URI.encode_www_form([["email", node["kagent"]["dashboard"]["user"]], ["password", node["kagent"]["dashboard"]["password"]]]) 
            
            response = http.request(request)

            if !response.kind_of? Net::HTTPSuccess
                raise "Error authenticating with the Hopsworks server"
            end

            # Take only the token
            master_token = response['Authorization'].split[1].strip
            jbody = JSON.parse(response.body)
            renew_tokens = jbody['renewTokens']

            return master_token, renew_tokens
        end

        def execute_shell_command(command)
          _, stdout, stderr, wait_thr = Open3.popen3(command)
          if not wait_thr.value.success?
            Chef::Application.fatal!("Error executing command #{command}. STDERR: #{stderr.readlines}",
                                     wait_thr.value.exitstatus)
          end
          Chef::Log.debug("Command: #{command} - STDOUT: #{stdout.readlines}")
        end
    end
end

Chef::Recipe.send(:include, Kagent::JWTHelper)
Chef::Resource.send(:include, Kagent::JWTHelper)
