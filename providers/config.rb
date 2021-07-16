action :add do

  begin
    ini_file = IniFile.load("#{new_resource.services_file}", :comment => ';#') # 
    group = "#{new_resource.service}"
    service = "#{new_resource.role}"

    #
    # A section name will have the format: ${GROUPNAME}-${SERVICENAME}
    # The SERVICENAME is allowed to include '-' (separator character), but the or groupname
    # is not allowed to include a '-' in their name
    # The SERVICENAME will be the actual name of the script as used by init.d and systemd.
    # The agent.py program will use start/stop/restart/status the service by calling, e.g., 
    # systemctl start SERVICENAME
    #
    section="#{group}-#{service}"
    Chef::Log.info "Loaded kagent groups ini-file #{ini_file} with : #{section}"

    if ini_file.has_section?(section)
      Chef::Log.info "Over-writing an existing section in the ini file."
      ini_file.delete_section(section)
    end
    ini_file[section] = {
      'group'  => "#{group}",
      'service'  => "#{service}",
      'stdout-file'  => "#{new_resource.log_file}",
      'config-file'  => "#{new_resource.config_file}",
      'fail-attempts' => new_resource.fail_attempts
    } 
    ini_file.save
    Chef::Log.info "Saved an updated copy of groups file at the kagent after updating #{group}-#{service}"

    bash "restart-kagent-after-update" do
      user "root"
      code <<-EOH
        systemctl restart kagent
      EOH
      not_if {new_resource.restart_agent == false}
    end
  rescue Exception => ex
    if node['kagent']['enabled'].casecmp?("true")
      raise ex
    else
      Chef::Log.warn "Error adding #{new_resource.service} to kagent service file but IGNORE because kagent is NOT enabled. Original error: #{ex.message}"
    end
  ensure
    new_resource.updated_by_last_action(true)
  end
end



action :systemd_reload do
  bash "start-if-not-running-#{new_resource.name}" do
    user "root"
    ignore_failure true
    code <<-EOH
     systemctl daemon-reload
     systemctl stop #{new_resource.name}
     systemctl reset-failed
     systemctl start #{new_resource.name}
    EOH
  end
end

