#-*- coding: utf-8 -*-

import flask
from flask_sockets import Sockets
from geventwebsocket.exceptions import WebSocketError
import gevent
from epics import PV
from epics.ca import CASeverityException
import json
import re
import time
from threading import Thread
from datetime import datetime

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

class SetpointTimeoutException(IOError):
    '''The magnet failed to reach the requested setpoint.'''


class Magnet(object):

    STATUS_READY = 'Ready'
    STATUS_TIMEOUT = 'Failed: Timeout'
    STATUS_CA_ERROR = 'Failed: Channel Access'
    STATUS_GOING_TO_MIN = 'Going to min'
    STATUS_GOING_TO_MAX = 'Going to max'
    STATUS_GOING_TO_INIT = 'Going to init'
    STATUS_PAUSING = 'Pausing'

    TIMEOUT = 60

    def __init__(self, prefix, name, min_sp=None, max_sp=None, **kws):
        super(Magnet, self).__init__()
        self.setpoint_pv = PV(prefix + ':CURRENT_SP')
        self.readback_pv = PV(prefix + ':CURRENT_MONITOR')
        self.name = name
        self.prefix = prefix
        self.tag = re.sub('[:-]', '_', prefix)
        self._cycle_status = self.STATUS_READY
        self.min_sp = min_sp
        self.max_sp = max_sp
        self.tolerance = 0.05
        self.cycling = False
        self.cycle_iterations = 3
        self.cycle_pause_time = 3.
        self.cycle_status_callbacks = []

    def add_callback(self, attr, callback, **kws):
        if attr == 'cycle_status':
            self.cycle_status_callbacks.append(callback)
        elif attr == 'setpoint':
            self.setpoint_pv.add_callback(callback, **kws)
        elif attr == 'readback':
            self.readback_pv.add_callback(callback, **kws)
        else:
            raise KeyError('Unknown attribute.')


    @property
    def setpoint(self):
        return self.setpoint_pv.get()

    @setpoint.setter
    def setpoint(self, value):
        self.setpoint_pv.put(value)

    @property
    def readback(self):
        return self.readback_pv.get()

    @property
    def cycle_status(self):
        return self._cycle_status

    @cycle_status.setter
    def cycle_status(self, value):
        changed = self._cycle_status != value
        self._cycle_status = value
        if changed and self.cycle_status_callbacks:
            kws = {'pvname': self.prefix + ':CYCLE_STATUS', 'value': value}
            for cb in self.cycle_status_callbacks:
                Thread(target=cb, kwargs=kws).start()

    def go_to_setpoint(self, value):
        self.setpoint = value
        start_time = time.time()
        while abs(self.readback - value) > self.tolerance:
            if time.time() - start_time > self.TIMEOUT:
                raise SetpointTimeoutException()
            time.sleep(1.)

    def cycle_iteration(self):
        self.cycle_status = self.STATUS_GOING_TO_MIN
        self.go_to_setpoint(self.min_sp)
        self.cycle_status = self.STATUS_PAUSING
        time.sleep(self.cycle_pause_time)
        self.cycle_status = self.STATUS_GOING_TO_MAX
        self.go_to_setpoint(self.max_sp)
        self.cycle_status = self.STATUS_PAUSING
        time.sleep(self.cycle_pause_time)

    def cycle(self):
        if self.cycling:
            return
        self.cycling = True

        init_sp = self.setpoint
        err = None
        for i in range(self.cycle_iterations):
            try:
                self.cycle_iteration()
            except SetpointTimeoutException:
                err = self.STATUS_TIMEOUT
                break
            except CASeverityException:
                err = self.STATUS_CA_ERROR
                break
        self.cycle_status = self.STATUS_GOING_TO_INIT
        try:
            self.go_to_setpoint(init_sp)
        except SetpointTimeoutException:
            err = self.STATUS_TIMEOUT
        except CASeverityException:
            err = self.STATUS_CA_ERROR
        if err:
            self.cycle_status = err
        else:
            self.cycle_status = u'✓ {0:%H:%M %d/%m}'.format(datetime.now())

        self.cycling = False

magnets = []

# Add Horizontal Correctors
for num in range(1, 25):
    prefix = 'PS-OCH-B-2-{0}'.format(num)
    name = 'OCH-B-2-{0}'.format(num)
    magnets.append(Magnet(prefix, name, min_sp=-4., max_sp=4.))

# Add Vertical Correctors
for num in range(1, 12):
    prefix = 'PS-OCV-B-2-{0}'.format(num if num != 9 else '09')
    name = 'OCV-B-2-{0}'.format(num)
    magnets.append(Magnet(prefix, name, min_sp=-4., max_sp=4.))

tag_to_magnet = {}
for magnet in magnets:
    tag_to_magnet[magnet.tag] = magnet
    magnet.add_callback('setpoint', callback)
    magnet.add_callback('readback', callback)
    magnet.add_callback('cycle_status', callback)

@app.route('/')
def index():
    return flask.render_template('index.html', magnets=magnets)

@app.route('/cycle', methods=['POST'])
def cycle():
    tags = flask.request.json
    try:
        magnets_to_cycle = [tag_to_magnet[tag] for tag in tags]
    except TypeError, KeyError:
        flask.abort(400)
    for magnet in magnets_to_cycle:
        gevent.spawn(magnet.cycle)
    return 'OK'

@app.route('/reset', methods=['POST'])
def reset():
    for magnet in magnets:
        magnet.cycle_status = Magnet.STATUS_READY
    return 'OK'

@sockets.route('/socket')
def socket(ws):
    ws_conns.append(ws)
    while True:
        message = ws.receive()
        if message is None:
            break
    ws_conns.remove(ws)
    ws.close()

