action :add do

  ini_file = IniFile.load("#{new_resource.services_file}", :comment => ';#') # 
  cluster = "#{node["kagent"]["cluster"]}"
  group = "#{new_resource.service}"
  service = "#{new_resource.role}"

#
# A section name will have the format: ${CLUSTERNAME}-${GROUPNAME}-${SERVICENAME}
# The SERVICENAME is allowed to include '-' (separator character), but the clustername or groupname
# is not allowed to include a '-' in their name
# The SERVICENAME will be the actual name of the script as used by init.d and systemd.
# The agent.py program will use start/stop/restart/status the service by calling, e.g., 
# systemctl start SERVICENAME
#
  if cluster.include?("-") || group.include?("-") 
    raise "Invalid cluster or group name. Cannot contain  '-'" 
  end
  section="#{cluster}-#{group}-#{service}"
  Chef::Log.info "Loaded kagent groups ini-file #{ini_file} with : #{section}"

  if ini_file.has_section?(section)
    Chef::Log.info "Over-writing an existing section in the ini file."
    ini_file.delete_section(section)
  end
  ini_file[section] = {
    'cluster' => "#{cluster}",
    'group'  => "#{group}",
    'service'  => "#{service}",
    'web-port' => new_resource.web_port,
    'stdout-file'  => "#{new_resource.log_file}",
    'config-file'  => "#{new_resource.config_file}",
    'fail-attempts' => new_resource.fail_attempts
  } 
  ini_file.save
  Chef::Log.info "Saved an updated copy of groups file at the kagent after updating #{cluster}-#{group}-#{service}"

  bash "restart-kagent-after-update" do
    user "root"
    code <<-EOH
     set -e
     service kagent restart
    EOH
    not_if {new_resource.restart_agent == false}
  end

  
  new_resource.updated_by_last_action(true)
end



action :systemd_reload do
  
  bash "start-if-not-running-#{new_resource.name}" do
    user "root"
    ignore_failure true
    code <<-EOH
     systemctl stop #{new_resource.name}
     systemctl daemon-reload
     systemctl reset-failed
     systemctl start #{new_resource.name}
    EOH
  end

end

