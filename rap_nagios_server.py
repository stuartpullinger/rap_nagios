#!/usr/bin/python
'''HTTP server responds to GET requests and returns success or fail depending
on underlying test results

Based on the tutorial here: http://www.acmesystems.it/python_httpd'''

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import subprocess
import optparse
import signal

def check_service(service_name):
    '''Takes a service_name string and runs the 'service service_name status'
    command. Returns True if the return code is 0, False otherwise.'''
    return_code = subprocess.call(['service', service_name, 'status'])
    return return_code == '0'

def check_process(process_name):
    '''Takes a process_name string and looks for the string in the output of
    'ps -u apel -o args'. Returns True if it is found, False otherwise.'''
    ps_command = ['ps', '-u', 'apel', '-o', 'args'] # ps -u apel -o args
    ps_process = subprocess.Popen(ps_command, stdout=subprocess.PIPE)
    ps_output = ps_process.stdout.read()
    return process_name in ps_output

class GetStatusHandler(BaseHTTPRequestHandler):
    '''This class handles a GET request. It runs several tests, combines the
    result and returns a Status code of 200 for pass, 500 for fail and 503
    for error.'''

    def do_GET(self):
        try:
            # Run the tests
            grid_ssm_status = check_service('apelssmreceive')
            grid_loader_status = check_service('apeldbloader')
            cloud_ssm_status = check_service('apelssmreceive-cloud')
            cloud_loader_status = check_service('apeldbloader-cloud')
            summariser_status = check_process('apelsummariser') # tests for grid or cloud summariser
        except Exception as test_fail:
            # If any tests fail to run,
            # respond with status code '503 Service Unavailable'
            self.send_response(503)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write('''<html>
                               <body>
                                <p>Unable to run tests:</p>
                                <p>%s</p>
                               </body>
                              </html>''' % test_fail.strerror)
            return

        # Create html page showing the status of the tests
        statuses = ['grid_ssm_status: %s' % str(grid_ssm_status),
                    'grid_loader_status: %s' % str(grid_loader_status),
                    'cloud_ssm_status: %s' % str(cloud_ssm_status),
                    'cloud_loader_status: %s' % str(cloud_loader_status),
                    'summariser_status: %s' % str(summariser_status)]
        status_html = "<html><body>%s</body></html>" % '</br>'.join(statuses)

        if     (grid_ssm_status and
                cloud_ssm_status and
                (grid_loader_status or summariser_status) and
                (cloud_loader_status or summariser_status)):
            # If the combined test result is a pass,
            # respond with a status code '200 OK'
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(status_html)
            return
        else:
            # Otherwise, respond with a status code '500 Internal Server Error'
            self.send_response(500)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(status_html)
            return

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-s', '--server', dest='server', type='string', default='',
                      help='Host name for server to bind to. Defaults to empty string.')
    parser.add_option('-p', '--port', dest='port', type='int', default=8080,
                      help='Port for server to listen on. Defaults to 8080.')
    (options, args) = parser.parse_args()
    try:
        # Create a web server and define the handler to manage the
        # incoming request
        server = HTTPServer((options.server, options.port), GetStatusHandler)
        print 'Started httpserver at ', options.server, ', on port ', options.port

        # Allow server to be shut down with SIGTERM
        def sigterm_handler(signum, frame):
            print 'SIGTERM received, shutting down the web server'
            server.server_close()
            exit()
        signal.signal(signal.SIGTERM, sigterm_handler)

        # Wait forever for incoming http requests
        server.serve_forever()

    except KeyboardInterrupt:
        print '^C received, shutting down the web server'
        server.server_close()
        exit()
