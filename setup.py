from setuptools import setup

setup(name='python-ssllabs',
      version='v1.1',
      packages=['ssllabs'],
      scripts=['ssllabs-cli.py'],
      install_requires=['requests'],
      url='https://github.com/takeshixx/python-ssllabs',
      license='Apache 2.0',
      author='takeshix')