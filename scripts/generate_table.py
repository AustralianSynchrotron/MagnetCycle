#!/usr/bin/env python

class Magnet(object):
    def __init__(self, plane, num):
        s = num if plane != 'V' or num != 9 else '09'
        self.name = 'OC{0}-B-2-{1}'.format(plane, num)
        code_base = 'PS_OC{0}_B_2-{1}'.format(plane, s)
        self.sp_code = code_base + '_CURRENT_SP'
        self.rb_code = code_base + '_CURRENT_MONITOR'
        self.st_code = code_base + '_CYCLE_STATUS'

def print_mag(mag):
    print '      <td>{0}</td>'.format(mag.name)
    print '      <td data-bind=\'text: {0}\'></td>'.format(mag.sp_code)
    print '      <td data-bind=\'text: {0}\'></td>'.format(mag.rb_code)
    print '      <td data-bind=\'text: {0}\'></td>'.format(mag.st_code)
    print '      <td><input type=\'checkbox\'/></td>'

print """<table>
  <colgroup>
    <col class='name'>
    <col class='value'>
    <col class='value'>
    <col class='status'>
    <col class='cycle'>
    <col class='spacer'>
    <col class='name'>
    <col class='value'>
    <col class='value'>
    <col class='status'>
    <col class='cycle'>
    <col class='spacer'>
    <col class='name'>
    <col class='value'>
    <col class='value'>
    <col class='status'>
    <col class='cycle'>
  </colgroup>
  <thead>
      <tr>
        <th>Name</th>
        <th>Setpoint</th>
        <th>Readback</th>
        <th>Status</th>
        <th>Cycle</th>
        <th></th>
        <th>Name</th>
        <th>Setpoint</th>
        <th>Readback</th>
        <th>Status</th>
        <th>Cycle</th>
        <th></th>
        <th>Name</th>
        <th>Setpoint</th>
        <th>Readback</th>
        <th>Status</th>
        <th>Cycle</th>
      </tr>
  </thead>
  <tbody>"""
for i in range(1, 13):
    print '    <tr>'
    if i < 12:
        mags = [Magnet('H', i), Magnet('H', i + 12), Magnet('V', i)]
    else:
        mags = [Magnet('H', i), Magnet('H', i + 12)]
    for j, mag in enumerate(mags):
        print_mag(mag)
        if j < 2:
            print '      <td></td>'
    if i == 12:
        for j in range(6):
            print '      <td></td>'
    print '    </tr>'
print '  </tbody>'
print '</table>'
