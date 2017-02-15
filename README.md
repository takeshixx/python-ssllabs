python-ssllabs
==============

A Python interface for the Qualys SSL Labs API. It can be used as a command line client for automation tasks or as a module which can be integrated in other projects. It is compatible with Python 2.x/3.x and just depends on the ```requests``` module.

## Features

* Resume running assessments.
* Verbose output, showing progress of running endpoint assessments.
* Retrieve assessments from cache.

## Using the CLI

The CLI by default only prints the scanning results as a JSON object to stdout. It is recommended to parse this output with tools like [jq](https://stedolan.github.io/jq/) to extract the preferred fields. The following examples show how specific fields can be extracted.

Show only the grade:

```bash
$ ssllabs-cli.py --use-cache github.com |jq ".endpoints[] | [.grade, .ipAddress]"             
[
  "A+",
  "192.30.253.112"
]
[
  "A+",
  "192.30.253.113"
]
```

Check if there are any issues with the provided certificates:

```bash
$ ssllabs-cli.py --use-cache github.com |jq -r ".endpoints[] | .details | .chain | .certs[] | .subject, .issues"
CN=github.com,O=GitHub, Inc.,L=San Francisco,ST=California,C=US,2.5.4.17=#13053934313037,STREET=88 Colin P Kelly, Jr Street,2.5.4.5=#130735313537353530,1.3.6.1.4.1.311.60.2.1.2=#130844656c6177617265,1.3.6.1.4.1.311.60.2.1.3=#13025553,2.5.4.15=#0c1450726976617465204f7267616e697a6174696f6e
0
CN=DigiCert SHA2 Extended Validation Server CA,OU=www.digicert.com,O=DigiCert Inc,C=US
0
CN=github.com,O=GitHub, Inc.,L=San Francisco,ST=California,C=US,2.5.4.17=#13053934313037,STREET=88 Colin P Kelly, Jr Street,2.5.4.5=#130735313537353530,1.3.6.1.4.1.311.60.2.1.2=#130844656c6177617265,1.3.6.1.4.1.311.60.2.1.3=#13025553,2.5.4.15=#0c1450726976617465204f7267616e697a6174696f6e
0
CN=DigiCert SHA2 Extended Validation Server CA,OU=www.digicert.com,O=DigiCert Inc,C=US
0
```

## Terms of Use

This is not an official SSL Labs project. Please make sure to read the official [Qualys SSL Labs Terms of Use](https://www.ssllabs.com/downloads/Qualys_SSL_Labs_Terms_of_Use.pdf).

Also you should

* only inspect sites and servers whose owners have given you permission to do so.
* be clear that this tool works by sending assessment requests to remote SSL Labs servers and that this information will
be shared with them.
