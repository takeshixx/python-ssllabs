#!/usr/bin/env python
import sys
import json
import time
import multiprocessing

try:
    import requests
except ImportError:
    print('requests module is not available')
    sys.exit(1)


__version__ = '1.0'
__author__ = 'takeshix@adversec.com'
__license__ = 'Apache 2.0'
__all__ = ['SSLLabsAssessment']


def parse_arguments():
    from argparse import ArgumentParser
    parser = ArgumentParser(description='Qualys SSL Labs API client v{version}'.format(version=__version__))
    parser.add_argument('host', help='hostname which should be assessed')
    parser.add_argument('--resume', action='store_true', default=False, help='get the status of a running assessment')
    parser.add_argument('--publish', action='store_true', default=False, help='publish results on public results board')
    parser.add_argument('--ignore-mismatch', action='store_true', default=False, help='certificate hostname mismatch does not stop assessment')
    parser.add_argument('--use-cache', action='store_true', default=False, help='accept cached results (if available)')
    parser.add_argument('--max-age', metavar='N', default=5, type=int, help='max age (in hours) of cached results')
    parser.add_argument('--api-url', metavar='URL', default=False, help='use another API URL than the default')
    parser.add_argument('-q', action='store_true', default=False, help='suppress any output, just print the results')
    parser.add_argument('-v', action='store_true', default=False, help='enable verbose output')
    parser.add_argument('-d', action='store_true', default=False, help='enable debug output')
    return parser.parse_args()


class SSLLabsAssessment(object):
    """A basic API interface which eases the creation of SSL Labs assessments.

    See the *analyze* function for more information.

    Note: This module defaults to the SSL Labs dev API in favour of advanced features like IPv6 support. Beware, this
    might change in future releases. See the following documentation sources for further information:

        * dev: https://github.com/ssllabs/ssllabs-scan/blob/master/ssllabs-api-docs.md
        * stable: https://github.com/ssllabs/ssllabs-scan/blob/stable/ssllabs-api-docs.md
    """
    API_URLS = [
        'https://api.dev.ssllabs.com/api/v2/',   # dev
        'https://api.ssllabs.com/api/v2/'       # stable
    ]
    API_URL = None
    MAX_ASSESSMENTS = 25
    CLIENT_MAX_ASSESSMENTS = 25
    CURRENT_ASSESSMENTS = 0
    DEBUG = False
    VERBOSE = False
    QUIET = False
    
    def __init__(self, host=None, debug=False, verbose=False, quiet=False, api_url=None, *args, **kwargs):
        if host:
            self.host = host

        if api_url:
            self.API_URL = api_url

        self.DEBUG = debug
        self.VERBOSE = verbose

        if quiet:
            self.QUIET = True
            self.DEBUG = False
            self.VERBOSE = False

    def set_host(self, host):
        """Set the target FQDN.

        This public function can be used to set the target FQDN after the object has already been initialized.
        """
        self.host = host

    def _die_on_error(self, msg):
        if msg:
            print(msg)
        sys.exit(1)

    def _handle_api_error(self, response):
        _status = response.status_code

        if _status == 200:
            return response
        elif _status == 400:
            self._die_on_error('[API] invocation error: {}'.format(response.text))
        elif _status == 429:
            self._die_on_error('[API] client request rate too high or too many new assessments too fast: {}'.format(response.text))
        elif _status == 500:
            self._die_on_error('[API] internal error: {}'.format(response.text))
        elif _status == 503:
            self._die_on_error('[API] the service is not available: {}'.format(response.text))
        elif _status == 529:
            self._die_on_error('[API] the service is overloaded: {}'.format(response.text))
        else:
            self._die_on_error('[API] unknown status code: {}, {}'.format(_status, response.text))

    def _check_api_info(self):
        try:
            if not self.API_URL:
                for url in self.API_URLS:
                    try:
                        response = self._handle_api_error(requests.get('{}/info'.format(url))).json()
                        self.API_URL = url
                        break
                    except requests.ConnectionError:
                        continue
            else:
                try:
                    response = self._handle_api_error(requests.get('{}/info'.format(self.API_URL))).json()
                except requests.ConnectionError:
                    self._die_on_error('[ERROR] Provided API URL is unavailable.')

            if not self.API_URL:
                self._die_on_error('[ERROR] SSL Labs APIs are down. Please try again later.')

            self.MAX_ASSESSMENTS = response.get('maxAssessments')
            self.CLIENT_MAX_ASSESSMENTS = response.get('clientMaxAssessments')
            self.CURRENT_ASSESSMENTS = response.get('currentAssessments')

            if self.MAX_ASSESSMENTS<=0:
                if self.DEBUG:
                    print('Rate limit reached')
                return False

            if not self.QUIET:
                print('[NOTICE] SSL Labs v{engine_version} (criteria version {criteria_version})'.format(
                    engine_version=response.get('engineVersion'),
                    criteria_version=response.get('criteriaVersion')
                ))
                print('[NOTICE] {server_message}'.format(
                    server_message=response.get('messages')[0]
                ))

            return True
        except Exception as e:
            if self.DEBUG:
                print(e)
            return False

    def _trigger_new_assessment(self):
        _url = '{api_url}analyze?host={host}&publish={publish}&ignoreMismatch={ignore_mismatch}'
        _url = _url.format(
            api_url=self.API_URL,
            host=self.host,
            publish=self.publish,
            ignore_mismatch=self.ignore_mismatch
        )
        if self.from_cache == 'on':
            _url += '&fromCache={from_cache}&maxAge={max_age}'
            _url = _url.format(
                from_cache=self.from_cache,
                max_age=self.max_age
            )
        else:
            _url += '&startNew=on'

        try:
            self._handle_api_error(requests.get(_url))
            return True
        except Exception as e:
            if self.DEBUG:
                print(e)
            return False

    def _poll_api(self):
        _url = '{api_url}analyze?host={host}&publish={publish}&ignoreMismatch={ignore_mismatch}'
        _url = _url.format(
            api_url=self.API_URL,
            host=self.host,
            publish=self.publish,
            ignore_mismatch=self.ignore_mismatch
        )
        if self.from_cache == 'on':
            _url += '&fromCache={from_cache}&maxAge={max_age}'
            _url = _url.format(
                from_cache=self.from_cache,
                max_age=self.max_age
            )

        try:
            return self._handle_api_error(requests.get(_url)).json()
        except Exception as e:
            if self.DEBUG:
                print(e)
            return False

    def _get_all_results(self):
        _url = '{api_url}analyze?host={host}&publish={publish}&all={return_all}&ignoreMismatch={ignore_mismatch}'
        _url = _url.format(
            api_url=self.API_URL,
            host=self.host,
            publish=self.publish,
            return_all=self.return_all,
            ignore_mismatch=self.ignore_mismatch
        )
        if self.from_cache == 'on':
            _url += '&fromCache={from_cache}&maxAge={max_age}'
            _url = _url.format(
                from_cache=self.from_cache,
                max_age=self.max_age
            )
        try:
            return self._handle_api_error(requests.get(_url)).json()
        except Exception as e:
            if self.DEBUG:
                print(e)
            return False

    def _get_detailed_endpoint_information(self, host, ip, from_cache='off'):
        url = '{api_url}/getEndpointData?host={host}&s={endpoint_ip}&fromCache={from_cache}'.format(
            api_url=self.API_URL,
            host=host,
            endpoint_ip=ip,
            from_cache=from_cache
        )

        while True:
            try:
                response = self._handle_api_error(requests.get(url)).json()
                print('[INFO] [{ip_address}] Progress: {progress}%, Status: {status}'.format(
                    ip_address=response.get('ipAddress'),
                    progress='{}'.format(response.get('progress')) if response.get('progress') > -1 else '0',
                    status=response.get('statusDetailsMessage')
                    )
                )
                if response.get('progress') == 100:
                    return
                elif response.get('progress') < 0:
                    time.sleep(10)
                else:
                    time.sleep(5)
            except KeyboardInterrupt:
                return
            except Exception as e:
                if self.DEBUG:
                    print(e)
                time.sleep(5)
                continue


    def analyze(self, host=None, publish='off', start_new='on', from_cache='off', max_age=5,
                return_all='done', ignore_mismatch='on', resume=False, *args, **kwargs):
        """Start the assessment process.

        This is basically a wrapper function for all the API communication which takes care of everything. Any non-default
        behaviour of assessment processes can be tweaked with arguments to this function.

        Providing a *host* containing the FQDN of the target system(s) is the only mandatory argument. All remaining
        arguments are optional.
        """
        if not self._check_api_info():
            return False

        if host:
            self.host = host
        elif not self.host:
            return False

        self.publish = publish
        self.start_new = start_new
        self.return_all = return_all
        self.from_cache = from_cache
        self.max_age = max_age
        self.ignore_mismatch = ignore_mismatch

        if not resume:
            if not self.QUIET:
                print('[INFO] Retrieving assessment for {}...'.format(self.host))

            if not self._trigger_new_assessment():
                return False
        else:
            if not self.QUIET:
                print('[INFO] Checking running assessment for {}'.format(self.host))

        while True:
            _status = self._poll_api()
            if _status.get('status') == 'IN_PROGRESS':
                if not self.QUIET and resume:
                    print('[INFO] Assessment is still in progress')
                break
            elif _status.get('status') == 'READY':
                if not self.QUIET and resume:
                    print(
                        '[INFO] No running assessment. Use --use-cache '+
                        'to receive a cached assessment, or start a new one.'
                    )
                    return
                else:
                    return self._get_all_results()
            elif _status.get('status') == 'ERROR':
                print('An error occured: {}'.format(_status.errors))
                return
            else:
                continue

        if self.VERBOSE:
            print('[INFO] Testing {} host(s)'.format(len(_status.get('endpoints'))))

        self.manager = multiprocessing.Manager()
        self.endpoint_jobs = []

        try:
            if self.VERBOSE:
                for endpoint in _status.get('endpoints'):
                    _process = multiprocessing.Process(
                            target=self._get_detailed_endpoint_information, args=(self.host, endpoint.get('ipAddress'))
                    )
                    self.endpoint_jobs.append(_process)
                    _process.start()

                for job in self.endpoint_jobs:
                    job.join()

            while True:
                _status = self._poll_api()

                if not _status:
                    break

                _host_status = _status.get('status')

                if _host_status == 'IN_PROGRESS':
                    if not self.QUIET:
                        sys.stdout.write('.')
                        sys.stdout.flush()
                    time.sleep(10)
                elif _host_status == 'READY':
                    return self._get_all_results()
                elif _host_status == 'ERROR':
                    print('[ERROR] An error occured: {}'.format(_status.errors))
                    return
                elif _host_status == 'DNS':
                    if self.VERBOSE:
                        print('[INFO] Resolving hostname')
                    time.sleep(4)
                else:
                    print('[INFO] Unknown host status: {}'.format(_host_status))
        except KeyboardInterrupt:
            pass
        except:
            return

            
def main():
    cli_args = parse_arguments()
    try:
        assessment = SSLLabsAssessment(
            host=cli_args.host,
            debug=cli_args.d,
            verbose=cli_args.v,
            quiet=cli_args.q,
            api_url=cli_args.api_url
        )
        info = assessment.analyze(
            ignore_mismatch='off' if cli_args.ignore_mismatch else 'on',
            from_cache='on' if cli_args.use_cache else 'off',
            max_age=cli_args.max_age,
            publish='on' if cli_args.publish else 'off',
            resume=cli_args.resume
        )

        if not info:
            if cli_args.d:
                print('[DEBUG] Got no report')
            return 1

        # TODO: Implement proper printing of some values
        print(json.dumps(info, indent=4, sort_keys=True))

        return 0
    except Exception as e:
        if cli_args.d:
            print(e)
        return 1


if __name__ == '__main__':
    sys.exit(main())
