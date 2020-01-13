actions :add

default_action :add

attribute :name, :kind_of => String, :name_attribute => true, :required => true 

attribute :user, :kind_of => String, :required => true 
attribute :group, :kind_of => String, :required => true
attribute :run_as, :kind_of => String, :required => true

attribute :script_name, :kind_of => String, :required => true
attribute :template, :kind_of => String
attribute :variables, :kind_of => Hash