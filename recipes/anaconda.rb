#
# Read notes on what needs to be done for pyspark here:
# http://blog.cloudera.com/blog/2015/09/how-to-prepare-your-apache-hadoop-cluster-for-pyspark-jobs/
#
include_recipe "conda::install"
include_recipe "conda::default"

#
# Download python wheels for tensorflow to be installed by kagent/conda for each project
#
url1 = node["tensorflow"]["py36"]["url"]
url2 = node["tensorflow"]["py27"]["url"]
for url in ["#{url1}","#{url2}"]
  bin=File.basename(url)
  remote_file "#{node['conda']['base_dir']}/pkgs/#{bin}" do
    #  checksum installer_checksum
    owner node['conda']['user']
    group node['conda']['group']
    source url
    mode 0755
    action :create
  end
end
