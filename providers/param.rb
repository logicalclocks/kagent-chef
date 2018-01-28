#
# param can be used to send values to a chef-solo node.
# Typically, return values from recipes are downloaded from a node to the Karamel server host using param.rb.
# That is, you acquire the return value(s) from a recipe using the param { action:add}. Then you pass the parameter
# to the next recipe (on another node) as a chef attribute
#

require 'json'

def deep_merge(h1, h2)
  h1.merge(h2) { |key, h1_elem, h2_elem| deep_merge(h1_elem, h2_elem) }
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
# 'w+' : Read and write access. Pointer is positioned at start of file.
# We will overwrite the file with a new json object.
  file = ::File.new(filename, "w+")
  if ::File.file?(filename) && (not ::File.zero?(filename))
     data_json = JSON.parse(file)
  else
     data_hash = Hash.new
  end

  data_hash = deep_merge(data_hash, entry_hash)
  file.puts(JSON.pretty_generate(data_hash))
  file.close
end

