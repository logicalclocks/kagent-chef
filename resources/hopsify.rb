actions :register_host, :generate_x509, :create_user_directory

attribute :user, :kind_of => String, :required => false, default: nil
attribute :password, :kind_of => String, :required => false, default: nil
attribute :crypto_directory, :kind_of => String, :required => false, default: nil
attribute :hopsworks_alt_url, :kind_of => String, :required => false, default: nil
attribute :common_name, :kind_of => String, :required => false, default: nil