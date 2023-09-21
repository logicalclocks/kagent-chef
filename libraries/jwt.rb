require 'uri'
require 'net/http'
require 'json'
require 'open3'

module Kagent
    module JWTHelper
        def get_service_jwt()
            
            hopsworks_hostname = private_recipe_hostnames("hopsworks", "default")[0]
            port = 8182
            if node.attribute?("hopsworks") &&
                node['hopsworks'].attribute?("internal") &&
                node['hopsworks']['internal'].attribute?("port")
                    port = node['hopsworks']['internal']['port']
            end

            url = URI.parse("https://#{hopsworks_hostname}:#{port}/hopsworks-api/api/auth/service")

            # Retry authenticating against Hopsworks in case of HTTP non-Success
            retries = 0
            response = http_request_follow_redirect(
              url, 
              body: URI.encode_www_form([["email", node["kagent"]["dashboard"]["user"]], ["password", node["kagent"]["dashboard"]["password"]]]),
              contenttype: 'application/x-www-form-urlencoded'
            ) 
            until response.kind_of? Net::HTTPSuccess or retries > 5 do
              Chef::Log.warn("Could not authenticate with Hopsworks, will retry in 30 sec.")
              sleep(30)
              response = http_request_follow_redirect(
                url, 
                body: URI.encode_www_form([["email", node["kagent"]["dashboard"]["user"]], ["password", node["kagent"]["dashboard"]["password"]]]),
                contenttype: 'application/x-www-form-urlencoded'
              ) 
              retries += 1
            end
            if !response.kind_of? Net::HTTPSuccess
              raise "Error authenticating with Hopsworks"
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
            raise "Error executing command #{command}. Return code: #{wait_thr.value.exitstatus} STDERR: #{stderr.readlines}"
          end
          Chef::Log.debug("Command: #{command} - STDOUT: #{stdout.readlines}")
        end

        def get_elk_signing_key()
          master_token, renew_tokens = get_service_jwt()
          hopsworks_hostname = private_recipe_hostnames("hopsworks", "default")[0]
          port = 8181
          if node.attribute?("hopsworks")
            if node['hopsworks'].attribute?("https")
              if node['hopsworks']['https'].attribute?("port")
                port = node['hopsworks']['https']['port']
              end
            end
          end

          url = URI("https://#{hopsworks_hostname}:#{port}/hopsworks-api/api/jwt/elk/key")

          http = Net::HTTP.new(url.host, url.port)

          # Don't verify the host certificate
          http.use_ssl = true
          http.verify_mode = OpenSSL::SSL::VERIFY_NONE

          request = Net::HTTP::Get.new(url)

          request["Content-Type"] = 'application/json'
          request['Authorization'] = "Bearer #{master_token}" 
                     
          response = http.request(request)

          if !response.kind_of? Net::HTTPOK
            raise "Error getting the elk signing key"
          end

          return response.body.strip
        end

    end
end

Chef::Recipe.send(:include, Kagent::JWTHelper)
Chef::Resource.send(:include, Kagent::JWTHelper)
