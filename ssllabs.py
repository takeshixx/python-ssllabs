#!/usr/bin/env python
import sys
import json
import time
import multiprocessing

API_URL = 'https://api.ssllabs.com/api/v2/'
DEBUG = False


def debug(msg=None):
   if DEBUG and msg:
       print('[DEBUG] {}'.format(msg))


def error(msg=None):
    if msg:
        print('[ERROR] {}'.format(msg))
    sys.exit(1)


def info(msg=None):
    if msg:
        print('[INFO] {}'.format(msg))


try:
    import requests
except ImportError:
    error('requests module is not available')


def parse_arguments():
    from argparse import ArgumentParser
    global cli_args
    parser = ArgumentParser()
    parser.add_argument('host', help='Hostname which should be scanned')
    parser.add_argument('--ignore-mismatch', action='store_true', default=False, help='Certificate hostname mismatch does not stop assessment')
    parser.add_argument('--use-cache', action='store_true', default=False, help='Accept cached results (if available)')
    parser.add_argument('-q', action='store_true', default=False, help='Suppress any output, just print the results')
    parser.add_argument('-v', action='store_true', default=False, help='Enable verbose output')
    parser.add_argument('-d', action='store_true', default=False, help='Enable debug output')
    cli_args = parser.parse_args()


class SSLLabsAssessment(object):
    MAX_ASSESSMENTS = 25
    CLIENT_MAX_ASSESSMENTS = 25
    CURRENT_ASSESSMENTS = 0
    DEBUG = False
    VERBOSE = False
    QUIET = False
    
    def __init__(self, host=None, debug=False, verbose=False, quiet=False):
        if host:
            self.host = host

        self.DEBUG = debug
        self.VERBOSE = verbose

        if quiet:
            self.QUIET = True
            self.DEBUG = False
            self.VERBOSE = False


    def set_host(self, host):
        self.host = host


    def _handle_api_error(self, response):
        _status = response.status_code

        if _status == 200:
            return response
        elif _status == 400:
            error('[API] invocation error: {}'.format(response.text))
        elif _status == 429:
            error('[API] client request rate too high or too many new assessments too fast: {}'.format(response.text))
        elif _status == 500:
            error('[API] internal error: {}'.format(response.text))
        elif _status == 503:
            error('[API] the service is not available: {}'.format(response.text))
        elif _status == 529:
            error('[API] the service is overloaded: {}'.format(response.text))
        else:
            error('[API] unknown status code: {}, {}'.format(_status, response.text))


    def _check_api_info(self):
        try:
            response = self._handle_api_error(requests.get('{}/info'.format(API_URL)))
            self.MAX_ASSESSMENTS = response.json().get('maxAssessments')
            self.CLIENT_MAX_ASSESSMENTS = response.json().get('clientMaxAssessments')
            self.CURRENT_ASSESSMENTS = response.json().get('currentAssessments')

            if self.MAX_ASSESSMENTS<=0:
                debug('Rate limit reached')
                return False

            return True
        except Exception as e:
            debug(e)
            return False


    def _trigger_new_assessment(self):
        _url = '{api_url}analyze?host={host}&publish={publish}&fromCache={from_cache}&'
        _url += 'maxAge={max_age}&all={return_all}&ignoreMismatch={ignore_mismatch}&startNew=on'
        _url = _url.format(
            api_url=API_URL,
            host=self.host,
            publish=self.publish,
            from_cache=self.from_cache,
            max_age=self.max_age,
            return_all=self.return_all,
            ignore_mismatch=self.ignore_mismatch
        )
        self._handle_api_error(requests.get(_url))


    def _poll_api(self):
        _url = '{api_url}analyze?host={host}&publish={publish}&fromCache={from_cache}&'
        _url += 'maxAge={max_age}&ignoreMismatch={ignore_mismatch}'
        _url = _url.format(
            api_url=API_URL,
            host=self.host,
            publish=self.publish,
            from_cache=self.from_cache,
            max_age=self.max_age,
            ignore_mismatch=self.ignore_mismatch
        )
        return self._handle_api_error(requests.get(_url)).json()


    def _get_all_results(self):
        _url = '{api_url}analyze?host={host}&publish={publish}&fromCache={from_cache}&'
        _url += 'maxAge={max_age}&all={return_all}&ignoreMismatch={ignore_mismatch}'
        _url = _url.format(
            api_url=API_URL,
            host=self.host,
            publish=self.publish,
            from_cache=self.from_cache,
            max_age=self.max_age,
            return_all=self.return_all,
            ignore_mismatch=self.ignore_mismatch
        )
        return self._handle_api_error(requests.get(_url)).json()


    def _get_detailed_endpoint_information(self, host, ip, from_cache='off'):
        url = '{api_url}/getEndpointData?host={host}&s={endpoint_ip}&fromCache={from_cache}'.format(
            api_url=API_URL,
            host=host,
            endpoint_ip=ip,
            from_cache=from_cache
        )

        try:
            while True:
                response = self._handle_api_error(requests.get(url)).json()

                if self.VERBOSE:
                    info('[{ip_address}] Progress: {progress}%, Status: {status}'.format(
                        ip_address=response.get('ipAddress'),
                        progress=response.get('progress'),
                        status=response.get('statusDetailsMessage')
                        )
                    )

                if response.get('progress') == 100:
                    return

                time.sleep(5)
        except KeyboardInterrupt:
            return


    def analyze(self, host=None, publish='off', start_new='on', from_cache='off',
        max_age=0, return_all='done', ignore_mismatch='on', *args, **kwargs):

        if not self._check_api_info():
            return False

        if host:
            self.host = host
        elif not self.host:
            return False

        self.publish = publish
        self.start_new = start_new
        self.from_cache = from_cache
        self.max_age = max_age
        self.return_all = return_all
        self.ignore_mismatch = ignore_mismatch
        self._trigger_new_assessment()

        if not self.QUIET:
            info('Assessment of {} started...'.format(self.host))

        while True:
            _status = self._poll_api()
            if _status.get('status') == 'IN_PROGRESS':
                break
            elif _status.get('status') == 'ERROR':
                error('An error occured: {}'.format(_status.errors))
            else:
                continue

        if self.VERBOSE:
            info('Testing {} host(s)'.format(len(_status.get('endpoints'))))

        self.manager = multiprocessing.Manager()
        self.endpoint_jobs = []

        try:
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
                    sys.stdout.write('.')
                    sys.stdout.flush()
                    time.sleep(10)
                elif _host_status == 'READY':
                    return self._get_all_results()
                elif _host_status == 'ERROR':
                    error('An error occured: {}'.format(_status.errors))
                elif _host_status == 'DNS':
                    if VERBOSE:
                        info('Resolving hostname')
                    time.sleep(4)
                else:
                    info('Unknown host status: {}'.format(_host_status))
        except KeyboardInterrupt:
            pass
        except:
            return False

            
def main():
    try:
        parse_arguments()

        if cli_args.d:
            DEBUG = True

        assessment = SSLLabsAssessment(
            host=cli_args.host,
            verbose=cli_args.v,
            quiet=cli_args.q
        )
        info = assessment.analyze(
            ignore_mismatch='off' if cli_args.ignore_mismatch else 'on',
            from_cache='on' if cli_args.use_cache else 'off'
        )

        if not info:
            debug('Got no report')
            return 1

        # TODO: Implement proper printing of some values
        print(info)
    except Exception as e:
        debug(e)
        return 1


if __name__ == '__main__':
    sys.exit(main())
