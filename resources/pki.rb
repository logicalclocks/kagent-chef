actions :sign_csr

attribute :csr_file, :kind_of => String
attribute :output_dir, :kind_of => String
attribute :ca_path, :kind_of => String
attribute :http_port, :kind_of => Integer
attribute :host, :kind_of => String, :default => "127.0.0.1"