class X509Helper
    def initialize(node)
        @node = node
    end

    #def get_crypto_dir(user_home)
    #    @node['x509']['crypto-dir'].gsub("\$\{HOME\}", user_home)
    #end

    def get_crypto_dir(username)
        @node['x509']['super-crypto']['dir'].gsub("\$\{USER\}", username)
    end

    def get_user_keystores_name(username)
        kstore = @node['x509']['keystores']['keystore'].gsub("\$\{USERNAME\}", username)
        tstore = @node['x509']['keystores']['truststore'].gsub("\$\{USERNAME\}", username)
        return kstore, tstore
    end

    def get_public_name(username)
        @node['x509']['public'].gsub("\$\{USERNAME\}", username)
    end

    def get_certificate_bundle_name(username)
        @node['x509']['certificate-bundle'].gsub("\$\{USERNAME\}", username)
    end

    def get_private_key_pkcs8_name(username)
        @node['x509']['private']['pkcs8'].gsub("\$\{USERNAME\}", username)
    end

    def get_private_key_pkcs1_name(username)
        @node['x509']['private']['pkcs1'].gsub("\$\{USERNAME\}", username)
    end

    def get_hops_ca_bundle_name()
        @node['x509']['ca']['bundle']
    end
end

class Chef
    class Recipe
        def x509_helper
            X509Helper.new(node)
        end
    end

    class Resource
        def x509_helper
            X509Helper.new(node)
        end
    end

    class Provider
        def x509_helper
            X509Helper.new(node)
        end
    end
end