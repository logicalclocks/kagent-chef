actions :generate, :return_publickey, :get_publickey, :append2ChefTrustAnchors

attribute :homedir, :kind_of => String, :name_attribute => true
attribute :cb_name, :kind_of => String
attribute :cb_recipe, :kind_of => String
attribute :cb_user, :kind_of => String
attribute :cb_group, :kind_of => String
attribute :hopsworks_alt_url, :kind_of => String, default: nil
attribute :crypto_dir, :kind_of => String