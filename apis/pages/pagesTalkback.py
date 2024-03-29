import logging
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
import traceback

logger = logging.getLogger(__name__)

class TalkbackButton(QPushButton):
    def __init__(self, config, widgets, osc):
        super().__init__("Talkback Settings")
        self.config = config
        self.widgets = widgets
        self.osc = osc
        self.pressed.connect(self.clicked)

    def clicked(self):
        if "Talkback" not in self.widgets["windows"]:
            self.widgets["windows"]["Talkback"] = TalkbackWindow(self.config, self.widgets, self.osc)
        
        self.widgets["windows"]["Talkback"].show()

        self.setDown(False)

class TalkbackWindow(QMainWindow):
    def __init__(self, config, widgets, osc):
        super().__init__()
        self.config = config
        self.widgets = widgets
        self.osc = osc

        vlayout = QVBoxLayout()
        try:
            label = QLabel("Specify who to talkback to. A checked box indicates that talkback is active for channel.")
            label.setMaximumHeight(20)
            vlayout.addWidget(label)

            self.talkbacks = {}

            if "iem" not in config["osc"]:
                if not self.osc["fohClient"].connected:
                    raise SystemError("Not Connected to FOH Mixer")
                if "talkback" not in config or "destination" not in config["talkback"]:
                    raise KeyError("talkback.destination is not specified in config.py")

                vlayout.addWidget(TalkbackAllButton(osc, self.talkbacks))
                vlayout.addWidget(TalkbackNoneButton(osc, self.talkbacks))

                command = "/config/talk/" + config["talkback"]["destination"] + "/destmap"
                self.bitmap = ["0"] * 18

                for chName in config["personal"]:
                    if "iem_bus" in config["personal"][chName]:
                        bus = config["personal"][chName]["iem_bus"]

                        hlayout = QHBoxLayout()
                        hlayout.addWidget(QLabel(chName + ":"))
                        hlayout.addWidget(TalkbackMeButton(osc, self.talkbacks, chName))
                        self.talkbacks[bus] = TalkbackOneBox(osc, self.bitmap, bus, command)
                        spacer = QWidget()
                        spacer.setFixedWidth(30)
                        hlayout.addWidget(spacer)
                        hlayout.addWidget(self.talkbacks[bus])
                        vlayout.addLayout(hlayout)
                
                self.osc["fohServer"].subscription.add(command, self.processOneSubscription)
            else:
                if not self.osc["iemClient"].connected:
                    raise SystemError("Not Connected to IEM Mixer")
                if "talkback" not in config or "channel" not in config["talkback"]:
                    raise KeyError("talkback.channel is not specified in config.py")

                vlayout.addWidget(TalkbackAllButton(osc, self.talkbacks))
                vlayout.addWidget(TalkbackNoneButton(osc, self.talkbacks))

                for chName in config["personal"]:
                    if "iem_bus" in config["personal"][chName]:
                        bus = config["personal"][chName]["iem_bus"]

                        hlayout = QHBoxLayout()
                        hlayout.addWidget(QLabel(chName + ":"))
                        hlayout.addWidget(TalkbackMeButton(osc, self.talkbacks, bus))
                        self.talkbacks[bus] = TalkbackTwoBox(config, osc, bus)
                        spacer = QWidget()
                        spacer.setFixedWidth(30)
                        hlayout.addWidget(spacer)
                        hlayout.addWidget(self.talkbacks[bus])
                        vlayout.addLayout(hlayout)

                        if bus == "st" or bus == "mono":
                            self.osc["iemServer"].subscription.add(config["talkback"]["channel"] + "/mix/" + bus, self.processTwoSubscription)
                        else:
                            self.osc["iemServer"].subscription.add(config["talkback"]["channel"] + "/mix/" + bus + "/on", self.processTwoSubscription)
        except Exception as ex:
            logger.error(traceback.format_exc())
            label = QLabel("Error: " + str(ex))
            label.setStyleSheet("color:red")
            vlayout.addWidget(label)
        
        widget = QWidget()
        widget.setLayout(vlayout)
        self.setCentralWidget(widget)
    
    def processOneSubscription(self, mixerName, message, arg):
        # Update bitmap
        binVal = bin(arg)[2:]
        for idx, x in enumerate(binVal):
            self.bitmap[idx + (18 - len(binVal))] = x

        # Match boxes to bitmap
        for bus in self.talkbacks:
            if bus == "st":
                self.talkbacks[bus].setChecked(self.bitmap[0] == "1")
            elif bus == "mono":
                self.talkbacks[bus].setChecked(self.bitmap[1] == "1")
            else:
                self.talkbacks[bus].setChecked(self.bitmap[18 - int(bus)] == "1")

    def processTwoSubscription(self, mixerName, message, arg):
        bus = message.split("/")[4]
        self.talkbacks[bus].setChecked(arg == 1)
    
    def closeEvent(self, a0):
        if "iem" not in self.config["osc"]:
            self.osc["fohServer"].subscription.remove("/config/talk/" + self.config["talkback"]["destination"] + "/destmap")
        else:
            for chName in self.config["personal"]:
                if "iem_bus" in self.config["personal"][chName]:
                    if self.config["personal"][chName]["iem_bus"] == "st" or self.config["personal"][chName]["iem_bus"] == "mono":
                        self.osc["iemServer"].subscription.remove(self.config["talkback"]["channel"] + "/mix/" + self.config["personal"][chName]["iem_bus"])
                    else:
                        self.osc["iemServer"].subscription.remove(self.config["talkback"]["channel"] + "/mix/" + self.config["personal"][chName]["iem_bus"] + "/on")

        del self.widgets["windows"]["Talkback"]

# 1 Mixer
class TalkbackOneBox(QCheckBox):
    def __init__(self, osc, bitmap, bus, command):
        super().__init__()
        self.osc = osc
        self.bitmap = bitmap
        self.index = 18
        if bus == "st":
            self.index = 0
        elif bus == "mono":
            self.index = 1
        else:
            self.index = 18 - int(bus)
        self.command = command
        self.setFixedWidth(20)
        self.stateChanged.connect(self.clicked)
    
    def clicked(self, value):
        try:
            self.bitmap[self.index] = "1" if value == 2 else "0"
            self.osc["fohClient"].send_message(self.command, int("".join(self.bitmap), 2))
        except Exception as ex:
            logger.error(traceback.format_exc())
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Talkback")
            dlg.setText("Error: " + str(ex))
            dlg.exec()

# 2 Mixers
class TalkbackTwoBox(QCheckBox):
    def __init__(self, config, osc, bus):
        super().__init__()
        self.osc = osc
        self.command = config["talkback"]["channel"] + "/mix/" + bus + "/on"
        if bus == "st" or bus == "mono":
            self.command = config["talkback"]["channel"] + "/mix/" + bus
        self.setFixedWidth(20)
        self.stateChanged.connect(self.clicked)
    
    def clicked(self, value):
        try:
            arg = 1 if value == 2 else 0
            self.osc["iemClient"].send_message(self.command, arg)
        except Exception as ex:
            logger.error(traceback.format_exc())
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Talkback")
            dlg.setText("Error: " + str(ex))
            dlg.exec()

class TalkbackAllButton(QPushButton):
    def __init__(self, osc, boxes):
        super().__init__("Talk to Everybody!")
        self.osc = osc
        self.boxes = boxes
        self.pressed.connect(self.clicked)
    
    def clicked(self):
        for name in self.boxes:
            self.boxes[name].setChecked(True)

        self.setDown(False)

class TalkbackNoneButton(QPushButton):
    def __init__(self, osc, boxes):
        super().__init__("Talk to Nobody¡")
        self.osc = osc
        self.boxes = boxes
        self.pressed.connect(self.clicked)
    
    def clicked(self):
        for name in self.boxes:
            self.boxes[name].setChecked(False)

        self.setDown(False)

class TalkbackMeButton(QPushButton):
    def __init__(self, osc, boxes, bus):
        super().__init__("Talk to just Me!")
        self.osc = osc
        self.boxes = boxes
        self.bus = bus
        self.pressed.connect(self.clicked)
        self.setFixedWidth(150)
    
    def clicked(self):
        for bus in self.boxes:
            if (bus == self.bus):
                self.boxes[bus].setChecked(True)
            else:
                self.boxes[bus].setChecked(False)

        self.setDown(False)