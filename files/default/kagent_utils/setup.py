from setuptools import setup

setup(name='kagent_utils',
      version='0.1',
      description='Utility classes for kagent and csr',
      url='http://hops.io',
      author='Antonios Kouzoupis',
      author_email='antonios.kouzoupis@ri.se',
      packages=['kagent_utils'],
      install_requires=[
          'ConfigParser',
          'logging',
          'netifaces'
      ],
      zip_safe=False)
