from setuptools import setup
from ssllabs import vars

setup(name='python-ssllabs',
    version=vars.version,
    packages=['ssllabs'],
    scripts=['ssllabs-cli.py'],
    install_requires=['requests'],
    url='https://github.com/takeshixx/python-ssllabs',
    license=vars.license,
    author='takeshix',
    author_email='takeshix@adversec.com')
