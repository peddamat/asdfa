#
# Server can be accessed from: http://192.168.1.147:8080/static/testit
#

from bottle import route, run, template
from bottle import static_file

@route('/hello/<name>')
def index(name='World'):
    return template('<b>Hello {{name}}</b>!', name=name)

@route('/static/<filename>')
def server_static(filename):
    return static_file(filename, root='/home/pi')

run(host='192.168.1.147', port=8080, debug=True)
