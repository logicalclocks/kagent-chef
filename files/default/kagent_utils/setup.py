from setuptools import setup

setup(name='kagent_utils',
      version='0.3',
      description='Utility classes for kagent and csr',
      url='https://www.logicalclocks.com',
      author='Antonios Kouzoupis',
      author_email='antonios@logicalclocks.com',
      packages=['kagent_utils', 'kagent_utils.monitoring'],
      zip_safe=False
      #setup_requires=["pytest-runner"],
      #tests_require=["pytest"]
)
