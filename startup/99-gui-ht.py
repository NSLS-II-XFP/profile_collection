import numpy as np

#TODO(mr): remove later, for dev/tests only:
import matplotlib.pyplot as plt
plt.ion()
from bluesky.utils import install_qt_kicker
install_qt_kicker()

from itertools import cycle

from matplotlib.backends.qt_compat import QtWidgets, QtCore, QtGui


import bluesky.plans as bp
import pandas as pd
import os


class ColumnWidget:
    def __init__(self, j):
        self._position = j
        cb = self.cb = QtWidgets.QGroupBox('Position {}'.format(j))
        cb.setCheckable(True)
        sb = self.sb = QtWidgets.QDoubleSpinBox()
        sb.setValue(10)
        sb.setMinimum(10)
        sb.setMaximum(20000)
        le = self.le = QtWidgets.QLineEdit('sample {}'.format(j))
        notes = self.notes = QtWidgets.QTextEdit(''.format(j))

        indicator = self.indicator = QtWidgets.QPushButton('Test')
        # indicator.setStyleSheet ('background-color: red;border-style: outset;border-width: 2px;border-radius: 200px;border-color: beige;font: bold 14px;min-width: 10em;padding: 6px;')

        width = self.width = 50
        color = self.color = 'green'

        colors = ['blue', 'red', 'green']
        self.cycler = cycle(colors)

        indicator.setStyleSheet('''QPushButton {{
                background-color: {color};
                color: white;
                border-style: solid;
                border-width: 1px;
                border-radius: {radius}px;
                border-color: {color};
                max-width: {width}px;
                max-height: {width}px;
                min-width: {width}px;
                min-height: {width}px;
            }}'''.format(width=width, radius=width/2, color=color))
        indicator.clicked.connect(self.change_color)

        # indicator.setFixedHeight(30)
        # indicator.setFixedWidth(30)

        # label.setStyleSheet('QLabel {background-color: green; color: white}')

        cb.toggled.connect(sb.setEnabled)
        cb.toggled.connect(le.setEnabled)
        cb.setChecked(True)

        f_layout = QtWidgets.QFormLayout()
        # f_layout.addRow('name', le)
        # f_layout.addRow('exposure[ms]', sb)
        # f_layout.addRow('notes', notes)
        f_layout.addRow('', indicator)

        cb.setLayout(f_layout)

    def change_color(self):
        color = next(self.cycler)
        width = self.width
        return self.indicator.setStyleSheet(f'''QPushButton {{
                background-color: {color};
                color: white;
                border-style: solid;
                border-width: 1px;
                border-radius: {width/2}px;
                border-color: {color};
                max-width: {width}px;
                max-height: {width}px;
                min-width: {width}px;
                min-height: {width}px;
            }}''')

    @property
    def enabled(self):
        return self.cb.isChecked()

    @property
    def md(self):
        return {'name': self.le.displayText(),
                'notes': self.notes.toPlainText()}

    @property
    def position(self):
        return self._position

    @property
    def exposure(self):
        return self.sb.value()

class DirectorySelector:
    '''
    A widget class deal with selecting and displaying path names
    '''

    def __init__(self, caption, path=''):
        self.cap = caption
        widget = self.widget = QtWidgets.QGroupBox(caption)
        notes = self.notes = QtWidgets.QTextEdit('')

        hlayout = QtWidgets.QHBoxLayout()
        self.label = label = QtWidgets.QLabel(path)
        short_desc = self.short_desc = QtWidgets.QLineEdit('')

        hlayout.addWidget(self.label)
        hlayout.addStretch()
        button = QtWidgets.QPushButton('')
        button.setIcon(QtGui.QIcon.fromTheme('folder'))
        button.clicked.connect(self.select_path)
        # hlayout.addWidget(button)

        f_layout = QtWidgets.QFormLayout()
        f_layout.addRow(button, hlayout)
        f_layout.addRow('short description', short_desc)
        # f_layout.addRow('overall notes', notes)

        widget.setLayout(f_layout)

    @QtCore.Slot(str)
    def set_path(self, path):
        if os.path.isdir(path):
            self.label.setText(path)
        else:
            raise Exception("path does not exist")

    # @QtCore.Slot()
    def select_path(self):
        cur_path = self.path
        if len(cur_path) == 0:
            cur_path = ''
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self.widget, caption=self.cap, directory=cur_path)

        if len(path) > 0:
            self.path = path
            return path
        else:
            path = None
        return path

    @property
    def path(self):
        return self.label.text()

    @path.setter
    def path(self, in_path):
        self.set_path(in_path)


class RunEngineControls:
    def __init__(self, RE, GUI, motors):

        self.RE = RE
        self.GUI = GUI
        self.motors = motors

        self.widget = button_widget = QtWidgets.QWidget() 
        button_layout = QtWidgets.QHBoxLayout()
        button_widget.setLayout(button_layout)

        self.label = label = QtWidgets.QLabel('Idle')
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setStyleSheet('QLabel {background-color: green; color: white}')
        button_layout.addWidget(label)

        # Run button to execute RE
        self.button_run = button_run = QtWidgets.QPushButton('Run')
        button_run.clicked.connect(self.run)
        button_layout.addWidget(button_run)

        # Run button to execute RE
        self.button_pause = button_pause = QtWidgets.QPushButton('Pause')
        button_pause.clicked.connect(self.pause)
        button_layout.addWidget(button_pause)

        self.info_label = info_label = QtWidgets.QLabel('Motors info')
        info_label.setAlignment(QtCore.Qt.AlignLeft)
        # label.setStyleSheet('QLabel {background-color: green; color: white}')
        button_layout.addWidget(info_label)

        self.RE.state_hook = self.handle_state_change
        self.handle_state_change(self.RE.state, None)

    def run(self):
        if self.RE.state == 'idle':
            self.RE(self.GUI.plan())
        else:
            self.RE.resume()

    def pause(self):
        if self.RE.state == 'running':
            self.RE.request_pause()
        elif self.RE.state == 'paused':
            self.RE.stop()

    def handle_state_change(self, new, old):
        # color = 'gray'
        # state = 'unknown'
        # button_run_enabled = False
        # button_pause_enabled = True
        # button_run_text = 'Run'
        # button_pause_text = 'Pause'
        if new == 'idle':
            state = 'Idle'
            color = 'green'
            button_run_enabled = True
            button_pause_enabled = False
            button_run_text = 'Run'
            button_pause_text = 'Pause'
        elif new == 'paused':
            state = 'Paused'
            color = 'blue'
            button_run_enabled = True
            button_pause_enabled = True
            button_run_text = 'Resume'
            button_pause_text = 'Stop'
        elif new == 'running':
            state = 'Running'
            color = 'red'
            button_run_enabled = False
            button_pause_enabled = True
            button_run_text = 'Run'
            button_pause_text = 'Pause'

        self.label.setStyleSheet(f'QLabel {{background-color: {color}; color: white}}')
        self.label.setText(state)

        self.info_label.setText(motors_positions(self.motors)) # TODO
        self.button_run.setEnabled(button_run_enabled)
        self.button_run.setText(button_run_text)
        self.button_pause.setEnabled(button_pause_enabled)
        self.button_pause.setText(button_pause_text)


class XFPSampleSelector:
    def __init__(self, h_pos, v_pos, rows=12, cols=8):
        self.window = window = QtWidgets.QMainWindow()
        window.setWindowTitle('XFP High-Throughput Multi-Sample Holder')

        # Main widget:
        mw = QtWidgets.QWidget()

        # Main layout containing slots and control layouts:
        main_layout = QtWidgets.QHBoxLayout()

        # Slots:
        slots_layout = QtWidgets.QGridLayout()

        self.slots = []
        for j in range(rows*cols):
            r, c = np.unravel_index(j, (rows, cols))
            cw = ColumnWidget(j)
            slots_layout.addWidget(cw.cb, r, c)
            self.slots.append(cw)

        main_layout.addLayout(slots_layout)

        # Controls:
        controls_layout = QtWidgets.QVBoxLayout()

        self.path_select = path = DirectorySelector('CSV path')
        self.re_controls = RunEngineControls(RE, self, motors=[msh, mshlift])

        controls_layout.addWidget(path.widget)
        controls_layout.addWidget(self.re_controls.widget)

        button_toggle_all = QtWidgets.QPushButton('Check/Uncheck')
        button_toggle_all.setCheckable(True)
        button_toggle_all.setChecked(True)
        button_toggle_all.toggled.connect(self.toggle_all)
        controls_layout.addWidget(button_toggle_all)

        # Button to align the holder:
        button_align = QtWidgets.QPushButton('Align')
        button_align.clicked.connect(self.align_ht)
        controls_layout.addWidget(button_align)

        main_layout.addLayout(controls_layout)

        mw.setLayout(main_layout)
        window.setCentralWidget(mw)

        self.h_pos = h_pos
        self.v_pos = v_pos

    def walk_values(self):
        return [{'exposure': d.exposure,
                 'position': d.position,
                 **d.md} for d in self.slots
                if d.enabled]

    def show(self):
        return self.window.show()

    def close(self):
        return self.window.close()

    def toggle_all(self, state):
        for column in self.slots:
            column.cb.setChecked(state)

    def align_ht(self):
        print(align_ht())

    def plan(self, file_name=None):
        reason = self.path_select.short_desc.displayText()
        run_notes = self.path_select.notes.toPlainText()
        if file_name is None:
            gui_path = self.path_select.path
            if gui_path and reason:
                fname = '_'.join(reason.split()) + '.csv'
                file_name = os.path.join(gui_path, fname)
        print(file_name)

        uid_list = []
        base_md = {'plan_name': 'msh'}
        if reason:
            base_md['reason'] = reason

        for gui_d in self.walk_values():
            d = dict(base_md)
            d.update(gui_d)

            yield from bp.abs_set(msh,
                                  self.h_pos[d['position']],
                                  group='msh')
            yield from bp.abs_set(mshlift,
                                  self.v_pos[d['position']],
                                  group='msh')

            # awlays want to wait at least 3 seconds
            yield from bp.sleep(3)
            yield from bp.wait('msh')

            self.re_controls.info_label.setText(motors_positions([msh, mshlift]))

            uid = (yield from xfp_plan_fast_shutter(d))
            #uid = (yield from bp.count([msh, mshlift], md=d))

            if uid is not None:
                uid_list.append(uid)

        if uid_list:
            columns = ('uid', 'name', 'exposure', 'notes')
            tbl = pd.DataFrame([[h.start[c] for c in columns]
                                for h in db[uid_list]], columns=columns)
            self.last_table = tbl
            if file_name is not None:
                tbl.to_csv(file_name, index=False)

        yield from bp.mv(msh, -275)


def motors_positions(motors):
    format_str = []
    motor_values = []
    for m in motors:
        format_str.append(f'{m.name}: {{}}')
        motor_values.append(round(m.read()[m.name]['value'], 3))
    return '\n'.join(format_str).format(*motor_values)


def xfp_plan_fast_shutter(d):
    # MR: for test only, remove later:
    return
    exp_time = d['exposure']/1000

    yield from bp.mv(dg, exp_time)
    #open the protective shutter
    yield from bp.abs_set(shutter, 'Open', wait=True)

    #fire the fast shutter and wait for it to close again

    yield from bp.mv(dg.fire, 1)
    yield from bp.sleep(exp_time*1.1)

    #close the protective shutter
    yield from bp.abs_set(shutter, 'Close', wait=True)

    return (yield from bp.count([msh, mshlift, # pin_diode
                                ], md=d))


h_pos = np.array(
      [[-18.,  -9.,   0.,   9.,  18.,  27.,  36.,  45.],
       [-18.,  -9.,   0.,   9.,  18.,  27.,  36.,  45.],
       [-18.,  -9.,   0.,   9.,  18.,  27.,  36.,  45.],
       [-18.,  -9.,   0.,   9.,  18.,  27.,  36.,  45.],
       [-18.,  -9.,   0.,   9.,  18.,  27.,  36.,  45.],
       [-18.,  -9.,   0.,   9.,  18.,  27.,  36.,  45.],
       [-18.,  -9.,   0.,   9.,  18.,  27.,  36.,  45.],
       [-18.,  -9.,   0.,   9.,  18.,  27.,  36.,  45.],
       [-18.,  -9.,   0.,   9.,  18.,  27.,  36.,  45.],
       [-18.,  -9.,   0.,   9.,  18.,  27.,  36.,  45.],
       [-18.,  -9.,   0.,   9.,  18.,  27.,  36.,  45.],
       [-18.,  -9.,   0.,   9.,  18.,  27.,  36.,  45.]])

v_pos = np.array(
      [[  0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.],
       [  9.,   9.,   9.,   9.,   9.,   9.,   9.,   9.],
       [ 18.,  18.,  18.,  18.,  18.,  18.,  18.,  18.],
       [ 27.,  27.,  27.,  27.,  27.,  27.,  27.,  27.],
       [ 36.,  36.,  36.,  36.,  36.,  36.,  36.,  36.],
       [ 45.,  45.,  45.,  45.,  45.,  45.,  45.,  45.],
       [ 54.,  54.,  54.,  54.,  54.,  54.,  54.,  54.],
       [ 63.,  63.,  63.,  63.,  63.,  63.,  63.,  63.],
       [ 72.,  72.,  72.,  72.,  72.,  72.,  72.,  72.],
       [ 81.,  81.,  81.,  81.,  81.,  81.,  81.,  81.],
       [ 90.,  90.,  90.,  90.,  90.,  90.,  90.,  90.],
       [ 99.,  99.,  99.,  99.,  99.,  99.,  99.,  99.]])

try:
    HTgui.close()
except NameError:
    pass
HTgui = XFPSampleSelector(h_pos, v_pos)


