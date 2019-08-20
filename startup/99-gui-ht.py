plt.ion()
from bluesky.utils import install_qt_kicker
install_qt_kicker()
from itertools import cycle
from matplotlib.backends.qt_compat import QtWidgets, QtCore, QtGui
from locate_slot import LetterNumberLocator
import copy


COLOR_SUCCESS = 'green'
COLOR_RUNNING = 'red'
COLOR_SELECTED = '#007dff'  # blue
COLOR_SKIPPED = 'gray'


def get_position_from_index(positions, field, idx):
    return positions[idx][field]


def get_index_from_position(positions, field, current_pos, tolerance=1e-8):
    for idx, pos in enumerate(positions):
        if abs(pos[field] - current_pos) < tolerance:
            return idx
    return None


class ColumnWidget:
    def __init__(self, j, *, filter_obj=None, data=None):
        self._position = j
        self.data = data

        self.cb = QtWidgets.QGroupBox(f'Slot: {j}')
        self.cb.setCheckable(True)

        self.sb = QtWidgets.QDoubleSpinBox()
        self.sb.setValue(10)
        self.sb.setMinimum(0)
        self.sb.setMaximum(20000)

        self.le = QtWidgets.QLineEdit(f'sample {j}')

        # Combo box for selection of the filter thickness:
        if filter_obj is None:
            raise ValueError(f'The filter object should be specified. Passed None')
        self.filter_obj = filter_obj
        self.wheel_positions = copy.deepcopy(self.filter_obj.wheel_positions)
        for i, pos in enumerate(self.wheel_positions):
            self.wheel_positions[i]['text'] = (f'Angle: {pos["angle"]} [{pos["angle_egu"]}] '
                                               f'Thickness: {pos["thickness"]} [{pos["thickness_egu"]}]')

        self.filter_combo = QtWidgets.QComboBox()
        self.filter_combo.addItems([x['text'] for x in self.wheel_positions])

        self.notes = QtWidgets.QTextEdit(f'{j}')

        self.label_text = ''

        self.indicator = QtWidgets.QPushButton()

        self.width = 30
        self.color = color = COLOR_SELECTED
        self.inactive_color = COLOR_SKIPPED

        self.indicator.setStyleSheet('''QPushButton {{
                background-color: {color};
                color: red;
                border-style: solid;
                border-width: 1px;
                border-radius: {radius}px;
                border-color: {color};
                max-width: {width}px;
                max-height: {width}px;
                min-width: {width}px;
                min-height: {width}px;
                font-size: 36px;
            }}'''.format(width=self.width, radius=self.width/2, color=self.color))
        self.indicator.clicked.connect(self.input_dialog)
        self.update_slot()  # update slot info with self.data

        # self.cb.toggled.connect(self.sb.setEnabled)
        # self.cb.toggled.connect(self.le.setEnabled)
        self.cb.toggled.connect(self.state_changed)
        self.cb.setChecked(self.sb.value() > 0)
        self.indicator.setEnabled(True)

        self.cb_layout = QtWidgets.QHBoxLayout()
        self.cb_layout.addWidget(self.indicator)

        self.cb.setLayout(self.cb_layout)
        self.cb.setAlignment(QtCore.Qt.AlignCenter)

        # Pop up window with parameters:
        self.popup_window = QtWidgets.QMainWindow()
        self.popup_window.setWindowTitle(self.label_text)

        self.popup_widget = QtWidgets.QGroupBox()
        self.popup_widget.setTitle(self.label_text)
        self.popup_layout = QtWidgets.QFormLayout()
        self.popup_widget.setLayout(self.popup_layout)
        self.popup_window.setCentralWidget(self.popup_widget)

        self.popup_layout.addRow('Name', self.le)
        self.popup_layout.addRow('Exposure [ms]', self.sb)
        self.popup_layout.addRow('Filter', self.filter_combo)
        self.popup_layout.addRow('Notes', self.notes)

        # Update tooltip values:
        self.sb.valueChanged.connect(self.tooltip_update)
        self.sb.valueChanged.connect(self.check_zero)
        self.le.textChanged.connect(self.tooltip_update)
        self.notes.textChanged.connect(self.tooltip_update)
        self.filter_combo.currentIndexChanged.connect(self.tooltip_update)

    def update_slot(self):
        if self.data is not None:
            self.label_text = f"Slot: {self.data['location']} / {self.data['slot']}"
            self.cb.setTitle(self.label_text)
            self.le.setText(str(self.data['name']))
            self.notes.setText(str(self.data['notes']))
            self.sb.setValue(float(self.data['exposure']))
            self.filter_combo.setCurrentIndex(self.data['filter'])
        self.tooltip_update()

    def input_dialog(self):
        self.popup_window.show()
        self.popup_window.activateWindow()

    def check_zero(self):
        if self.sb.value() == 0:
            self.cb.setChecked(False)
            self.state_changed()
            self.indicator.setEnabled(True)

    def tooltip_update(self):
        warning = ''
        self.indicator.setText('')
        if 0 <= self.sb.value() < 10:
            self.indicator.setText('X')
            warning = '<h1 style="color: red;">Minimum exposure time must be >= 10 ms</h1>'

        self.tooltip_text = f"""\
{warning}<table>
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
        <td>Filter:</td><td><b>{self.filter_combo.currentText()}</b></td>
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
                color: red;
                border-style: solid;
                border-width: 1px;
                border-radius: {width/2}px;
                border-color: {color};
                max-width: {width}px;
                max-height: {width}px;
                min-width: {width}px;
                min-height: {width}px;
                font-size: 36px;
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
        return self.sb.value()

    @property
    def filter(self):
        idx = self.filter_combo.currentIndex()
        txt = self.wheel_positions[idx]['text']
        return {'index': idx, 'text': txt}


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
        button = QtWidgets.QPushButton('Select folder')
        button.setIcon(QtGui.QIcon.fromTheme('folder'))
        button.clicked.connect(self.select_path)
        # hlayout.addWidget(button)

        f_layout = QtWidgets.QFormLayout()
        f_layout.addRow(button, None)
        f_layout.addRow(hlayout)
        f_layout.addRow('File template:', short_desc)
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


class FileSelector:
    '''
    A widget class to deal with selecting and displaying files
    '''
    def __init__(self, caption, path='', ext_widget=None, filter_obj=None):
        self.file_name = None
        self.ext_widget = ext_widget
        self.excel_data = None
        self.filter_obj = filter_obj

        self.cap = caption
        widget = self.widget = QtWidgets.QGroupBox(caption)
        notes = self.notes = QtWidgets.QTextEdit('')

        hlayout = QtWidgets.QHBoxLayout()
        self.label = label = QtWidgets.QLabel(path)
        short_desc = self.short_desc = QtWidgets.QLineEdit()
        short_desc.setReadOnly(True)

        hlayout.addWidget(self.label)
        # hlayout.addStretch()
        self.button_name = 'Select Excel file'
        button = QtWidgets.QPushButton(self.button_name)
        button.setIcon(QtGui.QIcon.fromTheme('file'))
        button.clicked.connect(self.select_file)

        f_layout = QtWidgets.QFormLayout()
        f_layout.addRow(button, hlayout)
        f_layout.addRow('Selected file:', short_desc)

        widget.setLayout(f_layout)

    def select_file(self):
        fname = QtWidgets.QFileDialog.getOpenFileName(
            None, 'Select Excel file', os.getcwd(),
        filter='*.xls, *.xlsx')
        self.file_name = fname[0]
        self.short_desc.setText(self.file_name)
        self.update_cells()

    def update_cells(self):
        self.excel_data = pd.read_excel(self.file_name,
                                        dtype={'Slot (0-95)': int,
                                               'Location': str,
                                               'Sample name': str,
                                               'Exposure time (ms)': float,
                                               'Filter Thickness (um)': float,
                                               'Notes': str},
                                        keep_default_na=False)
        self.excel_data.columns = ['slot',
                                   'location',
                                   'name',
                                   'exposure',
                                   'filter',
                                   'notes']
        for j in range(NUM_ROWS*NUM_COLS):
            thickness = self.excel_data['filter'][j]
            self.excel_data.at[j, 'filter'] = get_index_from_position(self.filter_obj.wheel_positions, 'thickness', thickness)
            self.ext_widget.slots[j].data = self.excel_data.iloc[j, :]
            self.ext_widget.slots[j].update_slot()


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
        if EpicsSignalRO(pps_shutter.enabled_status.pvname).value == 0 and not mode.test_mode:
            self.label.setText('Shutter\nnot\nenabled')
            self.label.setStyleSheet(f'QLabel {{background-color: red; color: white}}')
        else:
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

        width = 60
        height = 60
        self.label.setFixedHeight(width)
        self.label.setFixedWidth(height)
        self.label.setStyleSheet(f'QLabel {{background-color: {color}; color: white}}')
        self.label.setText(state)

        self.info_label.setText(f'Motors positions:\n\n{motors_positions(self.motors)}')
        self.button_run.setEnabled(button_run_enabled)
        self.button_run.setText(button_run_text)
        self.button_pause.setEnabled(button_pause_enabled)
        self.button_pause.setText(button_pause_text)


class XFPSampleSelector:
    def __init__(self, h_pos, v_pos, *, slot_index=(2, 0), rows=12, cols=8, load_pos_x=LOAD_POS_X, load_pos_y=LOAD_POS_Y, filter_obj=None):

        self.filter_obj = filter_obj

        self.window = window = QtWidgets.QMainWindow()
        window.setWindowTitle('XFP High-Throughput Multi-Sample Holder')

        self._slot_index = slot_index
        self._rows = rows
        self._cols = cols
        self.load_pos_x = load_pos_x
        self.load_pos_y = load_pos_y

        # Main widget:
        mw = QtWidgets.QWidget()

        # Main layout containing slots and control layouts:
        main_layout = QtWidgets.QHBoxLayout()

        # Slots:
        slots_layout = QtWidgets.QGridLayout()

        self.letter_number = LetterNumberLocator(num_cols=cols, num_rows=rows)

        field = 'thickness'
        current_thickness = getattr(self.filter_obj, field).read()[f'{getattr(self.filter_obj, field).name}']['value']
        current_index = get_index_from_position(self.filter_obj.wheel_positions, field, current_thickness, self.filter_obj._tolerance)

        self.slots = []
        for j in range(rows*cols):
            r, c = np.unravel_index(j, (rows, cols))
            data = {
                'location': self.letter_number.find_slot_by_1d_index(j),
                'slot': j,
                'name': '',
                'notes': '',
                'exposure': 0,
                'filter': current_index,
            }
            cw = ColumnWidget(j, data=data, filter_obj=self.filter_obj)
            slots_layout.addWidget(cw.cb, r, c)
            self.slots.append(cw)

        main_layout.addLayout(slots_layout)

        # Controls:
        self.controls_layout = controls_layout = QtWidgets.QVBoxLayout()

        # Import Excel file controls:
        self.import_file = import_file = FileSelector('Import Excel file', ext_widget=self, filter_obj=self.filter_obj)
        self.path_select = path = DirectorySelector('Export CSV file after run')
        self.re_controls = RunEngineControls(RE, self, motors=[ht.x, ht.y])

        controls_layout.addWidget(self.import_file.widget)
        controls_layout.addWidget(self.path_select.widget)
        controls_layout.addWidget(self.re_controls.widget)

        # Checkbox to enable/disable the protective shutter per each slot or per whole run
        self.checkbox_shutter = QtWidgets.QCheckBox('Preshutter per sample?')
        self.checkbox_shutter.setChecked(False)
        self.checkbox_shutter.setCheckable(True)
        controls_layout.addWidget(self.checkbox_shutter)

        # Test mode:
        self.checkbox_test_mode = QtWidgets.QCheckBox('Test mode')
        self.checkbox_test_mode.setChecked(mode.test_mode)
        self.checkbox_test_mode.setCheckable(True)
        self.checkbox_test_mode.clicked.connect(self.switch_test_mode)
        controls_layout.addWidget(self.checkbox_test_mode)

        # Check/Uncheck button:
        button_toggle_all = QtWidgets.QPushButton('Check/Uncheck')
        button_toggle_all.setCheckable(True)
        button_toggle_all.setChecked(True)
        self.toggle_all(False)
        button_toggle_all.toggled.connect(self.toggle_all)
        controls_layout.addWidget(button_toggle_all)

        # A button to move to the load position:
        self.button_load_pos = button_load_pos = QtWidgets.QPushButton('Move to load position')
        button_load_pos.clicked.connect(self.move_to_load_position)
        controls_layout.addWidget(button_load_pos)

        # Group of widgets for aligning of the holder:
        self.aligning_group = aligning_group = QtWidgets.QGroupBox('Align the holder:')

        self.align_layout = align_layout = QtWidgets.QVBoxLayout()
        self.align_controls_layout = align_controls_layout = QtWidgets.QHBoxLayout()
        self.align_fields_layout = align_fields_layout = QtWidgets.QHBoxLayout()

        align_layout.addLayout(align_controls_layout)
        align_layout.addLayout(align_fields_layout)

        self.align_controls_layout.setAlignment(QtCore.Qt.AlignTop)

        # Align button:
        button_align = QtWidgets.QPushButton('Align')
        button_align.clicked.connect(self.align_ht)

        # Combo box for selection of the detectors to be used for alignment:
        self.dets_combo = QtWidgets.QComboBox()
        self.dets_combo.addItems(ALIGN_DETS.keys())

        # Checkbox to hide the input fields:
        self.checkbox_manual_align = QtWidgets.QCheckBox('Manual alignment')
        self.checkbox_manual_align.setChecked(False)
        self.checkbox_manual_align.setCheckable(True)
        self.checkbox_manual_align.toggled.connect(self.show_align_fields)

        # Align fields:
        self.aligning_x_label = aligning_x_label = QtWidgets.QLabel('X:')
        self.aligning_y_label = aligning_y_label = QtWidgets.QLabel('Y:')

        self.aligning_x = aligning_x = QtWidgets.QDoubleSpinBox()
        self.aligning_x.setMinimum(-97.5)
        self.aligning_x.setMaximum(97.5)

        self.aligning_y = aligning_y = QtWidgets.QDoubleSpinBox()
        self.aligning_y.setMinimum(-99.5)
        self.aligning_y.setMaximum(99.5)

        self.align_reset()

        self.align_reset_button = align_reset_button = QtWidgets.QPushButton('Reset')
        align_reset_button.clicked.connect(self.align_reset)

        # Add the button and the fields to the layout:
        for w in [button_align, self.dets_combo, self.checkbox_manual_align]:
            align_controls_layout.addWidget(w)

        for w in [aligning_x_label, aligning_x, aligning_y_label, aligning_y, align_reset_button]:
            align_fields_layout.addWidget(w)
        align_fields_layout.addStretch()

        # Initial hiding of the input fields for alignment:
        self.show_align_fields()

        aligning_group.setLayout(align_layout)
        controls_layout.addWidget(aligning_group)
        aligning_group.setMaximumHeight(100)

        main_layout.addLayout(controls_layout)

        mw.setLayout(main_layout)
        window.setCentralWidget(mw)

        # TODO: update it during next major refactor:
        # self.update_location(slot_align_x, slot_align_y)
        self.h_pos = h_pos
        self.v_pos = v_pos

    def move_to_load_position(self):
        RE(bps.mv(ht.x, self.load_pos_x, ht.y, self.load_pos_y))  # load position

    def align_reset(self):
        try:
            self.aligning_x.setValue(HT_COORDS_OLD['x'][self._slot_index[0]])
            self.aligning_y.setValue(HT_COORDS_OLD['y'][self._slot_index[0]])
        except:
            self.aligning_x.setValue(HT_X_START)
            self.aligning_y.setValue(HT_Y_START)

    def _manual_align_is_checked(self):
        return self.checkbox_manual_align.isChecked()

    def show_align_fields(self):
        is_hidden = not self._manual_align_is_checked()
        for w in [self.aligning_x_label, self.aligning_x, self.aligning_y_label, self.aligning_y, self.align_reset_button]:
            w.setHidden(is_hidden)

    def walk_values(self, snake=True):
        rows = self._rows
        cols = self._cols
        # A 1d-array with bools (0/1) showing if the slot is enabled:
        self.enabled = np.zeros((rows*cols))
        for i in range(rows*cols):
            d = self.slots[i]
            if d.enabled:
                self.enabled[i] = 1

        # Convert it to 2d-array:
        self.enabled = self.enabled.reshape((rows, cols))

        # A 2d-array with the indices of the slots:
        self.trajectory = np.arange(rows*cols).reshape((rows, cols))

        # Prepare the snake trajectory
        non_empty_rows = []
        if snake:
            for i in range(self.enabled.shape[0]):
                if 1 in self.enabled[i, :]:
                    non_empty_rows.append(i)
            for i, i_real in enumerate(non_empty_rows):
                if i % 2 != 0:
                    self.trajectory[i_real, :] = self.trajectory[i_real, ::-1]

        # List of return values:
        return_list = []
        for i in self.trajectory.reshape(rows*cols):
            d = self.slots[i]
            if d.enabled:
                return_list.append({'exposure': d.exposure,
                                    'position': d.position,
                                    'filter_index': d.filter['index'],
                                    'filter_text': d.filter['text'],
                                    **d.md})
        return return_list

    def walk_rows(self, snake=True):
        """

        returns
        -------
        [((row_num, x_start, x_stop, y, filter, exposure), [sample1, sample2, ...]),
         ...
         ]
        """
        rows = self._rows
        cols = self._cols
        # A 1d-array with bools (0/1) showing if the slot is enabled:
        self.enabled = np.zeros((rows*cols), dtype=int)
        for i in range(rows*cols):
            d = self.slots[i]
            if d.enabled:
                self.enabled[i] = 1

        # Convert it to 2d-array:
        self.enabled = self.enabled.reshape((rows, cols))

        # We start from the first X position -10 mm to reach the desired speed,
        # and finish 10 mm after the last position in the row of 8 slots.
        x_start, x_stop = HT_COORDS['x'][0] - 10.0, HT_COORDS['x'][self._cols-1] + 10.0
        return_list = []
        for i, row in enumerate(self.enabled):
            if not np.sum(row):
                continue
            samples = []
            for j in np.where(row)[0]:
                 d = self.slots[cols*i + j]
                 if not d.enabled:
                      continue
                 samples.append({'exposure': d.exposure,
                                 'position': d.position,
                                 'filter_index': d.filter['index'],
                                 'filter_text': d.filter['text'],
                                 **d.md})

            if not samples:
                raise RuntimeError('you found a bug?')
            filt = samples[0]['filter_index']
            exposure = samples[0]['exposure']
            return_list.append(
                ((i, x_start, x_stop, HT_COORDS['y'][i * self._cols], filt, exposure), samples))
            if snake:
                x_start, x_stop = x_stop, x_start

        return return_list

    def show(self):
        return self.window.show()

    def close(self):
        return self.window.close()

    def toggle_all(self, state):
        for column in self.slots:
            column.cb.setChecked(state and column.sb.value() > 0)
            column.indicator.setEnabled(True)

    def reset_colors(self):
        for slot in self.slots:
            if slot.cb.isChecked():
                slot.change_color(COLOR_SELECTED)

    def switch_test_mode(self, state):
        mode.test_mode = state

    def align_ht(self):
        kwargs = {'det': ALIGN_DETS[self.dets_combo.currentText()]}
        if self._manual_align_is_checked():
            kwargs['x_start'] = self.aligning_x.value()
            kwargs['y_start'] = self.aligning_y.value()
            kwargs['run'] = False
        self.dets_combo.setEnabled(False)
        RE(align_ht(**kwargs))
        self.dets_combo.setEnabled(True)
        self.update_locations(HT_COORDS['x'][self._slot_index[0]],
                              HT_COORDS['y'][self._slot_index[1]])

    def set_test(self):
        for i in [(0, 10, 0), (2, 20, 1), (29, 30, 2)]:
            column = self.slots[i[0]]
            column.cb.setChecked(True)
            column.indicator.setEnabled(True)
            column.sb.setValue(i[1])
            column.filter_combo.setCurrentIndex(i[2])

    def update_locations(self, slot_align_x, slot_align_y):
        d = default_coords(x_start=slot_align_x, y_start=slot_align_y,
                           x_init_slot=self._slot_index[0], y_init_slot=self._slot_index[1],
                           n_cols=self._cols, n_rows=self._rows)
        self.h_pos = d['x']
        self.v_pos = d['y']

    def plan(self, file_name=None):

        def close_shutters():
            yield from bps.mv(pre_shutter, 'Close')
            yield from bps.mv(pps_shutter, 'Close')
            yield from bps.mv(ht.x, self.load_pos_x, ht.y, self.load_pos_y)  # load position

        def main_plan(file_name):
            # Reset colors to the COLOR_SELECTED before each run:
            self.reset_colors()

            reason = self.path_select.short_desc.displayText()
            run_notes = self.path_select.notes.toPlainText()
            if file_name is None:
                gui_path = self.path_select.path
                if gui_path and reason:
                    fname = '_'.join(reason.split()) + '.csv'
                    file_name = os.path.join(gui_path, fname)
            xfp_print(f'CSV file name: {file_name}')

            uid_list = []
            base_md = {'plan_name': 'ht'}
            if reason:
                base_md['reason'] = reason

            if not mode.test_mode:
                yield from bps.mv(pps_shutter, 'Open')

            for gui_d in self.walk_values():
                d = dict(base_md)
                d.update(gui_d)

                row_num, col_num = np.unravel_index(gui_d['position'], (self._rows, self._cols))

                xfp_print(f"Info: {d}")
                xfp_print(f"Slot #{gui_d['position']}: X={self.h_pos[gui_d['position']]}  Y={self.v_pos[gui_d['position']]}")
                self.slots[gui_d['position']].change_color(COLOR_RUNNING)

                yield from bps.abs_set(ht.x, self.h_pos[gui_d['position']],
                                       group='ht')
                yield from bps.abs_set(ht.y, self.v_pos[gui_d['position']],
                                       group='ht')

                # always want to wait at least 3 seconds
                yield from bps.sleep(3)
                yield from bps.wait('ht')

                self.re_controls.info_label.setText(motors_positions([ht.x, ht.y]))

                # Open it once, when the holder arrives to the first scanning point:
                if pre_shutter.status.get() == 'Not Open' and not self.checkbox_shutter.isChecked():
                    yield from bps.mv(pre_shutter, 'Open')

                # Check that the shutters are opened before collecting data:
                if not mode.test_mode:
                    if pps_shutter.status.get() == 'Not Open':
                        raise Exception(f'{pps_shutter.name} must be open to finish the scan')
                    if pre_shutter.status.get() == 'Not Open' and not self.checkbox_shutter.isChecked() :
                        raise Exception(f'{pre_shutter.name} must be open to finish the scan')

                uid = (yield from xfp_plan_fast_shutter(d,
                                                        shutter_per_slot=self.checkbox_shutter.isChecked()))

                self.slots[gui_d['position']].change_color(COLOR_SUCCESS)

                xfp_print(f'UID from xfp_plan_fast_shutter(): {uid}')
                if uid is not None:
                    uid_list.append(uid)

                yield from bps.checkpoint()

            if uid_list:
                columns = ('uid', 'name', 'exposure', 'filter_text', 'notes')
                tbl = pd.DataFrame([[h.start[c] for c in columns]
                                    for h in db[uid_list]], columns=columns)
                self.last_table = tbl
                if file_name is not None:
                    tbl.to_csv(file_name, index=False)

            # Close it once the walkthrough is done:
            if not self.checkbox_shutter.isChecked():
                yield from bps.mv(shutter, 'Close')

            from bluesky.utils import FailedStatus
            try:
                yield from bps.mv(pps_shutter, 'Close')
            except FailedStatus:
                yield from bps.mv(pps_shutter, 'Close')

        return (yield from bpp.finalize_wrapper(main_plan(file_name),
                                                close_shutters()))

    def fly_plan(self, file_name=None):

        def close_shutters():
            yield from bps.mv(pre_shutter, 'Close')
            yield from bps.mv(pps_shutter, 'Close')
            yield from bps.mv(ht.x, self.load_pos_x, ht.y, self.load_pos_y)  # load position

        def main_plan(file_name):
            # Reset colors to the COLOR_SELECTED before each run:
            self.reset_colors()

            reason = self.path_select.short_desc.displayText()
            run_notes = self.path_select.notes.toPlainText()
            if file_name is None:
                gui_path = self.path_select.path
                if gui_path and reason:
                    fname = '_'.join(reason.split()) + '.csv'
                    file_name = os.path.join(gui_path, fname)
            xfp_print(f'CSV file name: {file_name}')

            uid_list = []
            base_md = {'plan_name': 'ht_fly'}
            if reason:
                base_md['reason'] = reason

            if not mode.test_mode:
                yield from bps.mv(pps_shutter, 'Open')

            for (row_num, x_start, x_stop, y_height, filt, exposure), samples in self.walk_rows():
                for j in range(self._cols):
                    w = self.slots[row_num * self._cols + j]
                    if w.enabled:
                        w.change_color(COLOR_RUNNING)

                # Open it once, when the holder arrives to the first scanning point:
                if pre_shutter.status.get() == 'Not Open' and not self.checkbox_shutter.isChecked():
                    yield from bps.mv(pre_shutter, 'Open')

                # Check that the shutters are opened before collecting data:
                if not mode.test_mode:
                    if pps_shutter.status.get() == 'Not Open':
                        raise Exception(f'{pps_shutter.name} must be open to finish the scan')
                    if pre_shutter.status.get() == 'Not Open' and not self.checkbox_shutter.isChecked() :
                        raise Exception(f'{pre_shutter.name} must be open to finish the scan')
                velo = 5  # TODO make this a function of exposure and filter
                # def fly_row(x_motor, y_motor, start_pos, end_pos, row_height, target_speed, samples):
                # TODO: compute the velocity
                uids = yield from fly_row(ht.x, ht.y, filter_wheel, x_start, x_stop, y_height, velo, filt,
                                          [{**base_md, **s} for s in samples])

                for j in range(self._cols):
                    w = self.slots[row_num * self._cols + j]
                    if w.enabled:
                        w.change_color(COLOR_SUCCESS)

                if uids is not None:
                    uid_list.extend(uids)

                yield from bps.checkpoint()

            if uid_list:
                columns = ('uid', 'name', 'exposure', 'filter_text', 'notes')
                tbl = pd.DataFrame([[h.start[c] for c in columns]
                                    for h in db[uid_list]], columns=columns)
                self.last_table = tbl
                if file_name is not None:
                    tbl.to_csv(file_name, index=False)

            # Close it once the walkthrough is done:
            if not self.checkbox_shutter.isChecked():
                yield from bps.mv(shutter, 'Close')

            from bluesky.utils import FailedStatus
            try:
                yield from bps.mv(pps_shutter, 'Close')
            except FailedStatus:
                yield from bps.mv(pps_shutter, 'Close')

        return (yield from bpp.finalize_wrapper(main_plan(file_name),
                                                close_shutters()))

def motors_positions(motors):
    format_str = []
    motor_values = []
    for m in motors:
        format_str.append(f'{m.name}: {{}}')
        motor_values.append(round(m.read()[m.name]['value'], 3))
    return '\n'.join(format_str).format(*motor_values)


def xfp_plan_fast_shutter(d, shutter_per_slot):
    current_field = 'thickness'
    move_to_thickness = float(get_position_from_index(filter_wheel.wheel_positions,
                                                      current_field,
                                                      d['filter_index']))
    yield from bps.mv(getattr(filter_wheel, current_field), move_to_thickness)

    exp_time = d['exposure']/1000
    yield from bps.mv(dg, exp_time)

    if shutter_per_slot:
        yield from bps.mv(pre_shutter, 'Open')

    # fire the fast shutter and wait for it to close again
    yield from bps.mv(dg.fire, 1)
    yield from bps.sleep(exp_time*1.1)

    if shutter_per_slot:
        yield from bps.mv(pre_shutter, 'Close')

    return (yield from bp.count([ht.x, ht.y], md=d))


def fly_row(x_motor, y_motor, filt_motor, start_pos, end_pos, row_height, target_speed, filt_pos, samples):
    # yield from bps.mov(x_motor.velocity, x_motor.velocity.limits[1])
    move_to_thickness = float(get_position_from_index(filter_wheel.wheel_positions,
                                                      'thickness',
                                                      filt_pos))
    yield from bps.mov(x_motor, start_pos,
                       y_motor, row_height,
                       filt_motor, move_to_thickness)

    yield from bps.mov(x_motor.velocity, target_speed)

    yield from bps.mov(x_motor, end_pos)

    uids = []
    for sample in samples:
        uid = yield from bp.count([], md={'speed': target_speed, **sample})
        uids.append(uid)

    return uids

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

HTgui = XFPSampleSelector(x_pos, y_pos, filter_obj=filter_wheel)
