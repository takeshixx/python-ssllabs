from setuptools import setup

# Read the value of the 'version' variable from ssllabs/vars.py without importing it.
# Importing vars.py would cause the installation to fail if dependencies of ssllabs/__init__.py are not met.

import pathlib
import re

version = None

with open(pathlib.Path(__file__).parent / 'ssllabs' / 'vars.py') as f:
    for line in f:
        match = re.match(r'version = \'(.*)\'', line)
        if match:
            version = match.group(1)
            break

if not version:
    raise RuntimeError('Could not determine version from ssllabs/vars.py')

setup(name='python-ssllabs',
    version=version,
    packages=['ssllabs'],
    scripts=['ssllabs-cli.py'],
    install_requires=['requests'],
    url='https://github.com/takeshixx/python-ssllabs',
    license='Apache 2.0',
    author='takeshix',
    author_email='takeshix@adversec.com')
