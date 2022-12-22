
maintainer       "Jim Dowling"
maintainer_email "jdowling@kth.se"
name             "kagent"
license          "GPL 2.0"
description      "Installs/Configures the Karamel agent used by Hops"
long_description IO.read(File.join(File.dirname(__FILE__), 'README.md'))
version          "3.2.0"
source_url       "https://github.com/karamelchef/kagent-chef"


%w{ ubuntu debian centos }.each do |os|
  supports os
end

depends 'openssl', '~> 4.4.0'
depends 'hostsfile', '~> 2.4.5'
depends 'ntp', '~> 2.0.0'
depends 'sudo', '~> 4.0.0'
depends 'magic_shell', '~> 1.0.0'
depends 'conda'

recipe "kagent::install", "Installs the Karamel agent and python dependencies"
recipe "kagent::default", "Installs and configures the Karamel agent"
recipe "kagent::purge", "Deletes the Karamel agent files"
recipe "kagent::dev", "Development helper library"

attribute "kagent/user",
          :description => "Username to run kagent as",
          :type => 'string'

attribute "kagent/user_id",
          :description => "kagent user id. Default: 1514",
          :type => 'string'

attribute "kagent/group",
          :description => "group to run kagent as",
          :type => 'string'

attribute "kagent/group_id",
          :description => "kagent group id. Default: 1510",
          :type => 'string'

attribute "kagent/user-home",
          :description => "Home directory of kagent user",
          :type => 'string'

attribute "kagent/certs_user",
          :description => "User managing PKI and service certificates",
          :type => 'string'

attribute "kagent/certs_user_id",
          :description => "certs user id. Default: 1515",
          :type => 'string'

attribute "kagent/certs_group",
          :description => "Group having access to service certificates",
          :type => 'string'

attribute "kagent/certs_group_id",
          :description => "certs group id. Default: 1511",
          :type => 'string'

attribute "kagent/dir",
          :description => "Installation directory for kagent",
          :type => 'string'

attribute "kagent/enabled",
          :description => "Kagent enabled: default 'true'. Set to 'false' to disable it.",
          :type => 'string'

attribute "kagent/dns",
          :description => "Default 'false'. Set to 'true' to use fully qualified domain names for kagent hosts in Hopsworks.",
          :type => 'string'

attribute "kagent/hostid",
          :description => " One-time password used when registering the host",
          :type => 'string'

attribute "kagent/name",
          :description => "Cookbook name",
          :type => 'string'

attribute "kagent/password",
          :description => "Agent's password - needed to call REST APIs on the kagent",
          :type => 'string'

attribute "kagent/rest_api/user",
          :description => "kagent REST API username",
          :type => "string"

attribute "kagent/rest_api/password",
          :description => "kagent REST API  password",
          :type => "string"

attribute "kagent/dashboard/user",
          :description => "kagent username to register with server",
          :type => "string"

attribute "kagent/dashboard/password",
          :description => "kagent password to register with server",
          :type => "string"

attribute "systemd",
          :description => "Use systemd startup scripts, default 'true'",
          :type => "string"

attribute "ntp/install",
          :description => "Install Network Time Protocol (default: false)",
          :type => "string"

attribute "services/enabled",
          :description => "Default 'false'. Set to 'true' to enable daemon services, so that they are started on a host restart.",
          :type => "string"

attribute "certs/dir",
          :description => "Installation directory for ssl/tls certs",
          :type => 'string'

attribute "hops/dir",
          :description => "Installation directory for Hops",
          :type => 'string'

attribute "kagent/hopsify/version",
          :description => "Version of hopsify tool",
          :type => "string"

attribute "kagent/hopsify/bin_url",
          :description => "Download URL of hopsify tool",
          :type => "string"

attribute "kagent/cloud/monitor_interval",
          :description => "interval in seconds to check for cloud events",
          :type => "string"

attribute "kagent/cloud/monitor_url",
          :description => "URL from which to pull cloud events",
          :type => "string"
