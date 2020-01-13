action :add do 
    # Make sure the directory exists before writing the template 
    directory node["install"]["sudoers"]["scripts_dir"] do
        owner 'root'
        group 'root'
        mode '0711'
        action :create
    end

    template "#{node["install"]["sudoers"]["scripts_dir"]}/#{new_resource.script_name}" do
        source new_resource.template
        owner  'root'
        group  new_resource.group 
        mode   '0750'
        action :create
    end

    sudo new_resource.name do 
        commands    ["#{node["install"]["sudoers"]["scripts_dir"]}/#{new_resource.script_name}"]
        users       new_resource.user
        runas       new_resource.run_as
        nopasswd    true
        only_if     { node["install"]["sudoers"]["rules"].casecmp("true") == 0 }
    end 
end