require 'uri'
require 'net/http'

module Kagent
    module JWTHelper
        def get_service_jwt()
            
            hopsworks_ip = private_recipe_ip("hopsworks", "default")
            port = 8181
            if node.attribute?("hopsworks")
                if node['hopsworks'].attribute?("secure_port") 
                    port = node['hopsworks']['secure_port']
                end
            end

            url = URI("https://#{hopsworks_ip}:#{port}/hopsworks-api/api/auth/login")
            
            http = Net::HTTP.new(url.host, url.port)
            # Don't verify the host certificate
            http.verify_mode = OpenSSL::SSL::VERIFY_NONE

            request = Net::HTTP::Post.new(url)

            request["Content-Type"] = 'application/x-www-form-urlencoded'
            request.body = URI.encode_www_form([["email", node["kagent"]["dashboard"]["user"]], ["password", node["kagent"]["dashboard"]["password"]]]) 
            
            response = http.request(request)

            if response.kind_of? Net::HTTPSuccess
                raise "Error authenticating with the Hopsworks server"
            end

            return response['Authorization']
        end
    end
end