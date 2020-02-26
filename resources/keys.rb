actions :generate, :return_publickey, :get_publickey, :csr, :combine_certs, :generate_elastic_admin_certificate

attribute :homedir, :kind_of => String, :name_attribute => true, :required => true
attribute :cb_name, :kind_of => String
attribute :cb_recipe, :kind_of => String
attribute :cb_user, :kind_of => String, :required => true
attribute :cb_group, :kind_of => String, :required => true
attribute :hopsworks_alt_url, :kind_of => String, default: nil
