from PyQt6.QtWidgets import (
    QMessageBox,
    QPushButton,
)
from util.defaultOSC import MIDIClient

class ConnectMidiButton(QPushButton):
    def __init__(self, osc, name, status, port):
        super().__init__("Connect")
        self.osc = osc
        self.name = name
        self.status = status
        self.port = port
        self.init()
        self.pressed.connect(self.connect)
        self.setFixedWidth(80)
    
    def connect(self):
        if (self.init()):
            dlg = QMessageBox(self)
            dlg.setWindowTitle("MIDI Connection")
            dlg.setText("Connected to " + self.port.currentText() + " port")
            dlg.exec()
        else:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("MIDI Connection")
            dlg.setText("Unable to connect to " + self.port.currentText() + " port")
            dlg.exec()
        
        self.setDown(False)

    def init(self):
        self.osc[self.name + "Midi"] = MIDIClient(self.port.currentText())
        if (self.osc[self.name + "Midi"].open_output()):
            self.status.setText("Connected!")
            self.status.setStyleSheet("color: green")
            return True
        else:
            self.status.setText("INVALID")
            self.status.setStyleSheet("color: red")

            return False