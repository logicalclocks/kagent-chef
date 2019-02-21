from setuptools import setup

setup(name='kagent_utils',
      version='0.1',
      description='Utility classes for kagent and csr',
      url='http://hops.io',
      author='Antonios Kouzoupis',
      author_email='antonios.kouzoupis@ri.se',
      packages=['kagent_utils', 'kagent_utils.monitoring'],
      install_requires=[
          'ConfigParser',
          'logging',
          'netifaces',
          'ipy'
      ],
      zip_safe=False
      #setup_requires=["pytest-runner"],
      #tests_require=["pytest"]
)
