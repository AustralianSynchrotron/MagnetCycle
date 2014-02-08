#-*- coding: utf-8 -*-

import flask
from flask_sockets import Sockets
from geventwebsocket.exceptions import WebSocketError
from epics import Device
import json

app = flask.Flask(__name__)
app.debug = True
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

    attrs = ('CURRENT_SP', 'CURRENT_MONITOR')

    STATUS_READY = 'Ready'
    STATUS_GOING_TO_MIN = 'Going to min'
    STATUS_GOING_TO_MAX = 'Going to max'

    def __init__(self, prefix, label, min_sp=None, max_sp=None, **kws):
        self.label = label
        self.base_code = prefix.replace(':', '_').replace('-', '_')
        self.cycle_status = self.STATUS_READY
        self.min_sp = min_sp
        self.max_sp = max_sp
        self.pause_time = 3.
        super(Magnet, self).__init__(prefix=prefix, delim=':', attrs=self.attrs, **kws)

    @property
    def setpoint(self):
        return self.get('CURRENT_SP')

    @property
    def readback(self):
        return self.get('CURRENT_MONITOR')

magnets = []

# Add Horizontal Correctors
for num in range(1, 25):
    prefix = 'PS-OCH-B-2-{0}'.format(num)
    label = 'OCH-B-2-{0}'.format(num)
    magnets.append(Magnet(prefix, label, min_sp=-4., max_sp=4.))

# Add Vertical Correctors
for num in range(1, 12):
    prefix = 'PS-OCV-B-2-{0}'.format(num if num != 9 else '09')
    label = 'OCV-B-2-{0}'.format(num)
    magnets.append(Magnet(prefix, label, min_sp=-4., max_sp=4.))

for magnet in magnets:
    magnet.add_callback('CURRENT_SP', callback)
    magnet.add_callback('CURRENT_MONITOR', callback)

@app.route('/')
def index():
    return flask.render_template('index.html', magnets=magnets)

@sockets.route('/socket')
def socket(ws):
    ws_conns.append(ws)
    while True:
        message = ws.receive()
        if message is None:
            break
    ws_conns.remove(ws)
    ws.close()

