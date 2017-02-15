from setuptools import setup
import ssllabs

setup(name='python-ssllabs',
    version=ssllabs.__version__,
    packages=['ssllabs'],
    scripts=['ssllabs-cli.py'],
    install_requires=['requests'],
    url='https://github.com/takeshixx/python-ssllabs',
    license='Apache 2.0',
    author='takeshix')
