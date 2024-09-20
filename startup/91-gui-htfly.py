import copy
from enum import Enum

import pandas as pd
from matplotlib.backends.qt_compat import QtCore, QtGui, QtWidgets
from ophyd import EpicsSignalRO


class TestMode:
    def __init__(self, test_mode=False):
        self._test_mode = test_mode
        self._valid_values = (True, False)

    @property
    def test_mode(self):
        return self._test_mode

    @test_mode.setter
    def test_mode(self, test_mode):
        assert any(
            [test_mode is x for x in self._valid_values]
        ), f"The value should be one of {self._valid_values}"
        self._test_mode = test_mode


mode = TestMode(test_mode=False)


class LEDState(Enum):
    QUEUED = QtCore.Qt.blue
    COLLECTING = QtCore.Qt.red
    COMPLETE = QtCore.Qt.green
    NOT_QUEUED = QtCore.Qt.gray


class LedIndicator(QtWidgets.QLabel):
    def __init__(self, parent=None):
        super(LedIndicator, self).__init__(parent)
        self.setFixedSize(20, 20)  # Set the size of the LED
        self.state: LEDState = LEDState.NOT_QUEUED

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # Color based on state
        # color = (
        #    QtGui.QColor(QtCore.Qt.green) if self.state else QtGui.QColor(QtCore.Qt.red)
        # )
        color = QtGui.QColor(self.state.value)

        painter.setBrush(QtGui.QBrush(color))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawEllipse(0, 0, self.width(), self.height())  # Draw circle

    def setState(self, state: LEDState):
        self.state = LEDState(state)
        self.update()  # This will trigger a repaint


class RunEngineControls:
    def __init__(self, RE, GUI, motors):

        self.RE = RE
        self.GUI = GUI
        self.motors = motors

        self.widget = button_widget = QtWidgets.QWidget()
        button_layout = QtWidgets.QHBoxLayout()
        button_widget.setLayout(button_layout)

        self.label = label = QtWidgets.QLabel("Idle")
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setStyleSheet("QLabel {background-color: green; color: white}")
        button_layout.addWidget(label)

        # Run button to execute RE
        self.button_run = button_run = QtWidgets.QPushButton("Run")
        button_run.clicked.connect(self.run)
        button_layout.addWidget(button_run)

        # Run button to execute RE
        self.button_pause = button_pause = QtWidgets.QPushButton("Pause")
        button_pause.clicked.connect(self.pause)
        button_layout.addWidget(button_pause)

        self.info_label = info_label = QtWidgets.QLabel("Motors info")
        info_label.setAlignment(QtCore.Qt.AlignLeft)
        # label.setStyleSheet('QLabel {background-color: green; color: white}')
        button_layout.addWidget(info_label)

        self.RE.state_hook = self.handle_state_change
        self.handle_state_change(self.RE.state, None)

    def run(self):
        if (
            EpicsSignalRO(pps_shutter.enabled_status.pvname).get() == 0
            and not mode.test_mode
        ):
            self.label.setText("Shutter\nnot\nenabled")
            self.label.setStyleSheet(f"QLabel {{background-color: red; color: white}}")
        else:
            if self.RE.state == "idle":
                self.RE(self.GUI.plan())
            else:
                self.RE.resume()

    def pause(self):
        if self.RE.state == "running":
            self.RE.request_pause()
        elif self.RE.state == "paused":
            self.RE.stop()

    def handle_state_change(self, new, old):
        new = "idle"
        if new == "idle":
            color = "green"
            button_run_enabled = True
            button_pause_enabled = False
            button_run_text = "Run"
            button_pause_text = "Pause"
        elif new == "paused":
            color = "blue"
            button_run_enabled = True
            button_pause_enabled = True
            button_run_text = "Resume"
            button_pause_text = "Stop"
        elif new == "running":
            color = "red"
            button_run_enabled = False
            button_pause_enabled = True
            button_run_text = "Run"
            button_pause_text = "Pause"
        else:
            color = "darkGray"
            button_run_enabled = False
            button_pause_enabled = False
            button_run_text = "Run"
            button_pause_text = "Stop"

        state = str(new).capitalize()

        width = 60
        height = 60
        self.label.setFixedHeight(width)
        self.label.setFixedWidth(height)
        self.label.setStyleSheet(f"QLabel {{background-color: {color}; color: white}}")
        self.label.setText(state)

        self.info_label.setText(
            f"HTFly motor positions:\n\n{motors_positions(self.motors)}"
        )
        self.button_run.setEnabled(button_run_enabled)
        self.button_run.setText(button_run_text)
        self.button_pause.setEnabled(button_pause_enabled)
        self.button_pause.setText(button_pause_text)


def motors_positions(motors):
    format_str = []
    motor_values = []
    for m in motors:
        format_str.append(f"{m.name}: {{}}")
        motor_values.append(round(m.read()[m.name]["value"], 3))
    return "\n".join(format_str).format(*motor_values)


class HTFlyGUI(QtWidgets.QMainWindow):
    led_color_change_signal = QtCore.Signal(int, LEDState)

    def __init__(self, parent=None, filter_obj=None) -> None:
        super(HTFlyGUI, self).__init__(parent)
        self.setWindowTitle("XFP High Throughput Fly Device")
        self.main_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.main_widget)
        self.wheel_positions = [
            {
                "name": "Position 1",
                "angle": 0,
                "thickness": 0,
                "angle_egu": "deg",
                "thickness_egu": "um",
            },
            {
                "name": "Position 2",
                "angle": 45,
                "thickness": 762,
                "angle_egu": "deg",
                "thickness_egu": "um",
            },
            {
                "name": "Position 3",
                "angle": 90,
                "thickness": 508,
                "angle_egu": "deg",
                "thickness_egu": "um",
            },
            {
                "name": "Position 4",
                "angle": 135,
                "thickness": 305,
                "angle_egu": "deg",
                "thickness_egu": "um",
            },
            {
                "name": "Position 5",
                "angle": 180,
                "thickness": 203,
                "angle_egu": "deg",
                "thickness_egu": "um",
            },
            {
                "name": "Position 6",
                "angle": 225,
                "thickness": 152,
                "angle_egu": "deg",
                "thickness_egu": "um",
            },
            {
                "name": "Position 7",
                "angle": 270,
                "thickness": 76,
                "angle_egu": "deg",
                "thickness_egu": "um",
            },
            {
                "name": "Position 8",
                "angle": 315,
                "thickness": 25,
                "angle_egu": "deg",
                "thickness_egu": "um",
            },
        ]
        if filter_obj:
            self.filter_obj = filter_obj
            self.wheel_positions = copy.deepcopy(self.filter_obj.wheel_positions)
        for i, pos in enumerate(self.wheel_positions):
            self.wheel_positions[i]["text"] = (
                f'Angle: {pos["angle"]} [{pos["angle_egu"]}] '
                f'Thickness: {pos["thickness"]} [{pos["thickness_egu"]}]'
            )
        self._create_layout()
        self.led_color_change_signal.connect(self.change_led_color)

    def change_led_color(self, position, color: LEDState):
        print(f"Changing LED color! {color}")
        self.widget_rows[position][1].setState(color)

    def _create_layout(self):
        self.widget_layout = QtWidgets.QGridLayout(self)
        self.main_widget.setLayout(self.widget_layout)
        self._add_labels()
        self._add_widgets()

    def _add_labels(self):
        labels = [
            "Selector",
            "Status",
            "Sample ID",
            "Exposure\nTime (ms)",
            "Attenuation",
        ]
        for i, label in enumerate(labels):
            self.widget_layout.addWidget(QtWidgets.QLabel(label), 0, i)

    def _add_widgets(self):
        self.widget_rows = []
        for row in range(1, 7):
            checkbox = QtWidgets.QCheckBox(f"Row {row}")
            checkbox.row_num = row - 1
            checkbox.stateChanged.connect(
                lambda state, cb=checkbox: self.check_toggled(cb, state)
            )
            led_indicator = LedIndicator()
            sample_id_label = QtWidgets.QLineEdit(f"Sample {row}")
            exposure_time_label = QtWidgets.QLineEdit("0")
            onlyInt = QtGui.QDoubleValidator()
            exposure_time_label.setValidator(onlyInt)
            attenuation_dropdown = QtWidgets.QComboBox()
            if self.wheel_positions:
                attenuation_dropdown.addItems([x["text"] for x in self.wheel_positions])
            widgets = [
                checkbox,
                led_indicator,
                sample_id_label,
                exposure_time_label,
                attenuation_dropdown,
            ]
            self.widget_rows.append(widgets)
            for col, widget in enumerate(widgets):
                self.widget_layout.addWidget(widget, row, col)

        # Adding import button
        import_button = QtWidgets.QPushButton("Import Excel Plan")
        self.checkbox_test_mode = QtWidgets.QCheckBox("Test mode")
        self.checkbox_test_mode.setChecked(mode.test_mode)
        self.checkbox_test_mode.setCheckable(True)
        self.checkbox_test_mode.clicked.connect(self.switch_test_mode)

        self.widget_layout.addWidget(self.checkbox_test_mode, 1, 5)
        self.widget_layout.addWidget(import_button, 2, 5)
        import_button.clicked.connect(self.import_excel_plan)
        self.re_controls = RunEngineControls(RE, self, motors=[htfly.x, htfly.y])
        self.widget_layout.addWidget(self.re_controls.widget, 3, 5)

    def switch_test_mode(self, state):
        mode.test_mode = state

    def check_toggled(self, checkbox, check_state):
        if check_state == QtCore.Qt.CheckState.Checked:
            led_state = LEDState.QUEUED
        elif check_state == QtCore.Qt.CheckState.Unchecked:
            led_state = LEDState.NOT_QUEUED
        self.widget_rows[checkbox.row_num][1].setState(led_state)

    def import_excel_plan(self):
        dialog = QtWidgets.QFileDialog()
        filename, _ = dialog.getOpenFileName(
            self, "Import Plan", filter="Excel (*.xlsx)"
        )
        if filename:
            df = pd.read_excel(filename)
            if not self.is_valid_excel(df):
                return
            df = self.cleanup_dataframe(df)
            self.populate_widgets(df)

    def cleanup_dataframe(self, df):
        df["Sample name"] = df["Sample name"].fillna("")
        df["Exposure time (ms)"] = df["Exposure time (ms)"].fillna(0)
        df["Filter Thickness (um)"] = df["Filter Thickness (um)"].fillna(0)
        df["Notes"] = df["Notes"].fillna("")

        return df

    def populate_widgets(self, df):
        for i, row in df.iterrows():
            widget_row = self.widget_rows[i]
            widget_row[0].setChecked(True)
            widget_row[2].setText(row["Sample name"])
            widget_row[3].setText(str(row["Exposure time (ms)"]))
            if not row["Sample name"] or row["Exposure time (ms)"] == 0:
                widget_row[0].setChecked(False)
            for i, pos in enumerate(self.wheel_positions):
                if pos["thickness"] == row["Filter Thickness (um)"]:
                    widget_row[4].setCurrentIndex(i)
                    break

            if row["Sample name"] == "" or row["Exposure time (ms)"] == 0:
                for widget in widget_row:
                    widget.setDisabled(True)
            else:
                for widget in widget_row:
                    widget.setDisabled(False)

    def is_valid_excel(self, df):
        if len(df) != 6:
            self.show_error_dialog(
                "Excel file does not contain exactly 6 rows, aborting import"
            )
            return False
        required_columns = [
            "Sample name",
            "Exposure time (ms)",
            "Filter Thickness (um)",
            "Notes",
        ]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            self.show_error_dialog(f"Missing columns: {(',').join(missing_columns)}")
            return False

        return True

    def plan(self):
        num_rows = 0
        for row_num, widget_row in enumerate(self.widget_rows):
            if widget_row[0].checkState() == QtCore.Qt.CheckState.Checked:
                self.led_color_change_signal.emit(row_num, LEDState.COLLECTING)
                exp_time = float(widget_row[3].text())
                al_thickness = self.wheel_positions[widget_row[4].currentIndex()][
                    "thickness"
                ]
                print(f"Experiment running {row_num} {exp_time} {al_thickness}")
                if exp_time.is_integer():
                    exp_time = int(exp_time)

                yield from htfly_exptime_row(row_num + 1, f"{exp_time}ms", al_thickness)
                self.led_color_change_signal.emit(row_num, LEDState.COMPLETE)
                num_rows += 1
        print(
            f"\nExposure set for {num_rows} row(s) completed, now closing the photon shutter and returning to load position.\n"
        )

        pps_shutter.set("Close")
        yield from bps.sleep(
            3
        )  # Allow some wait time for the shutter opening to finish
        yield from htfly_move_to_load()

    def show_error_dialog(self, message):
        dlg = QtWidgets.QMessageBox(self)
        dlg.setWindowTitle("Error")
        dlg.setText(message)
        dlg.exec()


HTFlygui = HTFlyGUI(filter_obj=filter_wheel)
