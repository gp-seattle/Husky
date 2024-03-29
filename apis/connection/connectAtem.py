import logging
import traceback
from PyQt6.QtWidgets import (
    QMessageBox,
    QPushButton,
)
from util.defaultOSC import AtemClient, AtemSubscriptionServer

logger = logging.getLogger(__name__)

class ConnectAtemButton(QPushButton):
    def __init__(self, config, osc, port):
        super().__init__("Set")
        self.config = config
        self.osc = osc
        self.port = port

        self.osc["atemServer"] = AtemSubscriptionServer()

        try:
            self.init()
        except Exception:
            logger.warning(traceback.format_exc())
        self.pressed.connect(self.connect)
        self.setFixedWidth(80)
    
    def connect(self):
        try:
            self.init()
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Atem Connection")
            dlg.setText("Sending Atem OSC commands to local port " + self.port.currentText())
            dlg.exec()
        except Exception as ex:
            logger.warning(traceback.format_exc())
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Atem Connection")
            dlg.setText("Error: " + str(ex))
            dlg.exec()

        self.setDown(False)

    def init(self):
        try:
            self.osc["atemClient"] = AtemClient(int(self.port.currentText()))
            self.port.connected()
        except Exception as ex:
            self.port.invalid()
            raise ex
        finally:
            self.config["atemPort"] = self.port.currentText()