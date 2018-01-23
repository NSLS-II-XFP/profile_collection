plt.ion()
from bluesky.utils import install_qt_kicker
install_qt_kicker()
from itertools import cycle
from matplotlib.backends.qt_compat import QtWidgets, QtCore, QtGui
from locate_slot import LetterNumberLocator


COLOR_SUCCESS = 'green'
COLOR_RUNNING = 'red'
COLOR_SELECTED = '#007dff'  # blue
COLOR_SKIPPED = 'gray'


class ColumnWidget:
    def __init__(self, j, data=None):
        self._position = j
        self.data = data

        self.cb = QtWidgets.QGroupBox(f'Slot: {j}')
        self.cb.setCheckable(True)

        self.sb = QtWidgets.QDoubleSpinBox()
        self.sb.setValue(10)
        self.sb.setMinimum(0)
        self.sb.setMaximum(20000)

        self.le = QtWidgets.QLineEdit(f'sample {j}')

        self.notes = QtWidgets.QTextEdit(f'{j}')

        self.label_text = ''

        if self.data is not None:
            self.label_text = f"Slot: {data['Location']} / {data['Slot (0-95)']}"
            self.cb.setTitle(self.label_text)
            self.le.setText(self.data['Sample name'])
            self.notes.setText(self.data['Notes'])
            self.sb.setValue(float(self.data['Exposure time (ms)']))

        self.indicator = QtWidgets.QPushButton()
        # indicator.setStyleSheet ('background-color: red;border-style: outset;border-width: 2px;border-radius: 200px;border-color: beige;font: bold 14px;min-width: 10em;padding: 6px;')

        self.width = 30
        self.color = color = COLOR_SELECTED
        self.inactive_color = COLOR_SKIPPED

        self.indicator.setStyleSheet('''QPushButton {{
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
            }}'''.format(width=self.width, radius=self.width/2, color=self.color))
        self.indicator.clicked.connect(self.input_dialog)
        self.tooltip_update()

        self.cb.toggled.connect(self.sb.setEnabled)
        self.cb.toggled.connect(self.le.setEnabled)
        self.cb.toggled.connect(self.state_changed)
        self.cb.setChecked(self.sb.value() > 0)

        self.cb_layout = QtWidgets.QHBoxLayout()
        self.cb_layout.addWidget(self.indicator)

        self.cb.setLayout(self.cb_layout)
        self.cb.setAlignment(QtCore.Qt.AlignCenter)

        # Pop up window with parameters:
        self.popup_window = QtWidgets.QMainWindow()
        self.popup_window.setWindowTitle(f'{self.label_text}')

        self.popup_widget = QtWidgets.QGroupBox()
        self.popup_widget.setTitle(self.label_text)
        self.popup_layout = QtWidgets.QFormLayout()
        self.popup_widget.setLayout(self.popup_layout)
        self.popup_window.setCentralWidget(self.popup_widget)

        self.popup_layout.addRow('Name', self.le)
        self.popup_layout.addRow('Exposure [ms]', self.sb)
        self.popup_layout.addRow('Notes', self.notes)

        # Update tooltip values:
        self.sb.valueChanged.connect(self.tooltip_update)
        self.le.textChanged.connect(self.tooltip_update)
        self.notes.textChanged.connect(self.tooltip_update)

    def input_dialog(self):
        self.popup_window.show()
        self.popup_window.activateWindow()

    def tooltip_update(self):
        self.tooltip_text = f"""\
<table>
    <tr>
        <td>Slot:</td><td><b>{self.label_text}</b></td>
    </tr>
    <tr>
        <td>Name:</td><td><b>{self.le.text()}</b></td>
    </tr>
    <tr>
        <td>Exposure:</td><td><b>{self.sb.value()}</b></td>
    </tr>
    <tr>
        <td>Notes:</td><td><i>{self.notes.toPlainText()}<i></td>
    </tr>
</table>
"""
        self.indicator.setToolTip(self.tooltip_text)

    def change_color(self, color=None):
        if not color:
            color = self.color
        else:
            self.color = color
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

    def state_changed(self):
        if self.cb.isChecked():
            color = COLOR_SELECTED
        else:
            color = COLOR_SKIPPED
        self.change_color(color=color)
        self.tooltip_update()

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
        self._exposure = self.sb.value()
        return self._exposure


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

        width = 50
        height = 50
        self.label.setFixedHeight(width)
        self.label.setFixedWidth(height)
        self.label.setStyleSheet(f'QLabel {{background-color: {color}; color: white}}')
        self.label.setText(state)

        self.info_label.setText(f'Motor position:\n\n{motors_positions(self.motors)}')
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

        self.rows = rows
        self.cols = cols

        self.slots = []

        self.excel_path = excel_path = str(PROFILE_STARTUP_PATH / 'examples/example.xlsx')
        self.excel_data = excel_data = pd.read_excel(excel_path)
        self.letter_number = LetterNumberLocator(num_cols=cols, num_rows=rows)

        for j in range(rows*cols):
            r, c = np.unravel_index(j, (rows, cols))
            cw = ColumnWidget(j, data=self.excel_data.iloc[j, :])  # label=self.letter_number.find_slot_by_1d_index(j))
            slots_layout.addWidget(cw.cb, r, c)
            self.slots.append(cw)

        main_layout.addLayout(slots_layout)

        # Controls:
        controls_layout = QtWidgets.QVBoxLayout()

        self.path_select = path = DirectorySelector('Export CSV path')
        self.import_file = import_file = DirectorySelector('Import Excel file')
        self.re_controls = RunEngineControls(RE, self, motors=[ht.x, ht.y])

        controls_layout.addWidget(self.path_select.widget)
        controls_layout.addWidget(self.import_file.widget)
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
            column.cb.setChecked(state and column.sb.value() > 0)

    def align_ht(self):
        RE(align_ht())

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
        base_md = {'plan_name': 'ht'}
        if reason:
            base_md['reason'] = reason

        for gui_d in self.walk_values():
            d = dict(base_md)
            d.update(gui_d)

            row_num, col_num = np.unravel_index(gui_d['position'], (self.rows, self.cols))

            print(f"Info: {d}")
            print(f"Slot #{gui_d['position']}: X={self.h_pos[gui_d['position']]}  Y={self.v_pos[gui_d['position']]}")
            self.slots[gui_d['position']].change_color(COLOR_RUNNING)

            yield from bps.abs_set(ht.x,
                                   self.h_pos[gui_d['position']],
                                   group='ht')
            yield from bps.abs_set(ht.y,
                                   self.v_pos[gui_d['position']],
                                   group='ht')

            # always want to wait at least 3 seconds
            yield from bps.sleep(3)
            yield from bps.wait('ht')

            self.re_controls.info_label.setText(motors_positions([ht.x, ht.y]))
            self.slots[gui_d['position']].change_color(COLOR_SUCCESS)

            uid = (yield from xfp_plan_fast_shutter(d))
            print(f'UID from xfp_plan_fast_shutter(): {uid}')
            if uid is not None:
                uid_list.append(uid)

        if uid_list:
            columns = ('uid', 'name', 'exposure', 'notes')
            tbl = pd.DataFrame([[h.start[c] for c in columns]
                                for h in db[uid_list]], columns=columns)
            self.last_table = tbl
            if file_name is not None:
                tbl.to_csv(file_name, index=False)

        yield from bps.mv(ht.x, -96, ht.y, -50)


def motors_positions(motors):
    format_str = []
    motor_values = []
    for m in motors:
        format_str.append(f'{m.name}: {{}}')
        motor_values.append(round(m.read()[m.name]['value'], 3))
    return '\n'.join(format_str).format(*motor_values)


def xfp_plan_fast_shutter(d):
    exp_time = d['exposure']/1000
    yield from bps.mv(dg, exp_time)

    # open the protective shutter
    yield from bps.abs_set(shutter, 'Open', wait=True)

    # fire the fast shutter and wait for it to close again
    yield from bps.mv(dg.fire, 1)
    yield from bps.sleep(exp_time*1.1)

    # close the protective shutter
    yield from bps.abs_set(shutter, 'Close', wait=True)

    return (yield from bp.count([ht.x, ht.y], md=d))

try:
    HTgui.close()
except NameError:
    pass

try:
    HT_COORDS = pd.read_csv(HT_COORDS_FILE, index_col=0)
except:
    HT_COORDS = default_coords()

x_pos = HT_COORDS['x']
y_pos = HT_COORDS['y']

HTgui = XFPSampleSelector(x_pos, y_pos)


