#-*- coding: utf-8 -*-

import flask
from flask_sockets import Sockets
from geventwebsocket.exceptions import WebSocketError
from epics import Device
import json

app = flask.Flask(__name__)
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True
sockets = Sockets(app)
ws_conns = []

def callback(pvname, value, **kws):
    message = json.dumps({'pvname': pvname, 'value': value})
    for ws in ws_conns:
        try:
            ws.send(message)
        except WebSocketError:
            pass

class Magnet(Device):
    def __init__(self, plane, number, **kws):
        prefix = 'PS-OC{0}-B-2-{1}'.format(plane, number)
        attrs = ('CURRENT_SP', 'CURRENT_MONITOR')
        self.base_code = prefix.replace(':', '_').replace('-', '_')
        self.cycle_status = 'Ready'
        super(Magnet, self).__init__(prefix=prefix, delim=':', attrs=attrs, **kws)
        self.add_callback('CURRENT_SP', callback)
        self.add_callback('CURRENT_MONITOR', callback)

    @property
    def setpoint(self):
        return self.get('CURRENT_SP')

    @property
    def readback(self):
        return self.get('CURRENT_MONITOR')

magnets = []
for num in range(1, 25):
    magnets.append(Magnet('H', num))
for num in range(1, 12):
    s = num if num != 9 else '09' # OCV-B-2-09 deviates from naming convention
    magnets.append(Magnet('V', s))

@app.route('/')
def index():
    return flask.render_template('index.html', magnets=magnets)

@sockets.route('/socket')
def echo_socket(ws):
    ws_conns.append(ws)
    while True:
        message = ws.receive()
        if message is None:
            break
    ws_conns.remove(ws)
    ws.close()

