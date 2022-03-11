#
# param can be used to send values to a chef-solo node.
# Typically, return values from recipes are downloaded from a node to the Karamel server host using param.rb.
# That is, you acquire the return value(s) from a recipe using the param { action:add}. Then you pass the parameter
# to the next recipe (on another node) as a chef attribute
#

require 'json'

class ::Hash
    def deep_merge(second)
        merger = proc { |key, v1, v2| Hash === v1 && Hash === v2 ? v1.merge(v2, &merger) : Array === v1 && Array === v2 ? v1 | v2 : [:undefined, nil, :nil].include?(v2) ? v1 : v2 }
        self.merge(second.to_h, &merger)
    end
end

action :add do

  path = "#{new_resource.path}"
  cookbook = "#{new_resource.cookbook}"
  recipe = "#{new_resource.recipe}"
  subrecipe = "#{new_resource.subrecipe}"
  subsubrecipe = "#{new_resource.subsubrecipe}"
  param = "#{new_resource.param}"
  value = "#{new_resource.value}"
  executing_cookbook = "#{new_resource.executing_cookbook}"
  executing_recipe = "#{new_resource.executing_recipe}"

# The result will be written to file in this json format
  if subrecipe.empty?
     entry_hash = {"#{cookbook}" => { "#{recipe}" => { "#{param}" => "#{value}" }}}
  elsif subsubrecipe.empty?
     entry_hash = {"#{cookbook}" => { "#{recipe}" => { "#{subrecipe}" => { "#{param}" => "#{value}" }}}}
  else
     entry_hash = {"#{cookbook}" => { "#{recipe}" => { "#{subrecipe}" => { "#{subsubrecipe}" => { "#{param}" => "#{value}" }}}}}
  end

  filename = "#{path}/#{executing_cookbook}__#{executing_recipe}__out.json"

  if ::File.file?(filename) && (not ::File.zero?(filename))
     file_content = ::File.read(filename)
     file_json = JSON.parse(file_content)
     data_hash = file_json.deep_merge(entry_hash)
  else
     data_hash = entry_hash
  end

  # We will overwrite the file with a new json object.
  file = ::File.new(filename, "w+")
  file.puts(JSON.pretty_generate(data_hash, ascii_only: true))
  file.close
end

