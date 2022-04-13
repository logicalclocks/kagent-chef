actions :add, :systemd_reload, :remove

attribute :services_file, :kind_of => String, :default => node["kagent"]["services"]
attribute :role, :kind_of => String, :name_attribute => true, :required => true
attribute :service, :kind_of => String, :required => true
attribute :log_file, :kind_of => String 
attribute :config_file, :kind_of => String, :default => ""
attribute :fail_attempts, :kind_of => Integer, :default => 1
attribute :command, :kind_of => String, :default => ""
attribute :command_user, :kind_of => String, :default => ""
attribute :command_script, :kind_of => String, :default => ""
attribute :restart_agent, :kind_of => [TrueClass, FalseClass], :default => true

default_action :add
