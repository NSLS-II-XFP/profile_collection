from enum import Enum

import pandas as pd
from qtpy import QtCore, QtGui, QtWidgets

from qtpy import QtCore, QtGui, QtWidgets


class LEDState(Enum):
    QUEUED = QtCore.Qt.white
    COLLECTING = QtCore.Qt.green
    COMPLETE = QtCore.Qt.blue
    FAILED = QtCore.Qt.red


class LedIndicator(QtWidgets.QLabel):
    def __init__(self, parent=None):
        super(LedIndicator, self).__init__(parent)
        self.setFixedSize(20, 20)  # Set the size of the LED
        self.state: LEDState = LEDState.QUEUED

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
        self.state = state
        self.update()  # This will trigger a repaint


class HTFlyGUI(QtWidgets.QMainWindow):

    def __init__(self, parent=None) -> None:
        super(HTFlyGUI, self).__init__(parent)
        self.setWindowTitle("XFP High Throughput Fly")
        self.main_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.main_widget)
        self._create_layout()

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
            led_indicator = LedIndicator()
            sample_id_label = QtWidgets.QLabel(f"Sample {row}")
            exposure_time_label = QtWidgets.QLabel(f"Exp time {row}")
            attenuation_dropdown = QtWidgets.QComboBox()
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
        self.widget_layout.addWidget(import_button, 2, 5)
        import_button.clicked.connect(self.import_excel_plan)

    def import_excel_plan(self):
        dialog = QtWidgets.QFileDialog()
        filename, _ = dialog.getOpenFileName(
            self, "Import Plan", filter="Excel (*.xlsx"
        )
        if filename:
            df = pd.read_excel(filename)
            # if "Sample ID" in df.columns:


if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    main = HTFlyGUI()
    main.show()

    app.exec_()
