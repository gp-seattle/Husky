from datetime import date, timedelta
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from util.defaultOSC import MIDIServer
from util.lock import OwnerLock
from uuid import uuid4

class MidiInputsButton(QPushButton):
    def __init__(self, config, osc, widgets):
        super().__init__("Edit MIDI Inputs")
        self.config = config
        self.osc = osc
        self.widgets = widgets
        self.pressed.connect(self.clicked)

        self.osc["serverMidi"] = {}
        for portName in self.config["serverMidi"]:
            self.osc["serverMidi"][portName] = MIDIServer(portName, self.osc, self.widgets)
            for param in self.config["serverMidi"][portName]:
                self.osc["serverMidi"][portName].addCallback(param)
            self.osc["serverMidi"][portName].open_ioPort()

    def clicked(self):
        MidiInputDialog(self.osc, self.widgets).exec()

        # Update config
        self.config["serverMidi"] = {}
        for portName in self.osc["serverMidi"]:
            self.config["serverMidi"][portName] = []
            callbacks = self.osc["serverMidi"][portName].getCallbacks()
            for id in callbacks:
                self.config["serverMidi"][portName].append(callbacks[id])

        self.setDown(False)

class MidiInputDialog(QDialog):
    def __init__(self, osc, widgets):
        super().__init__()
        self.osc = osc
        self.widgets = widgets

        # Init Tabs
        self.tabs = QTabWidget()
        initTabs(self.osc, self.widgets, self.tabs)

        vlayout = QVBoxLayout()

        hlayout = QHBoxLayout()
        label = QLabel("MIDI Input: ")
        label.setFixedWidth(150)
        hlayout.addWidget(label)

        address = QComboBox()
        address.setEditable(True)
        address.addItems(MIDIServer().get_ioport_names())
        address.setCurrentIndex(-1)
        
        hlayout.addWidget(address)
        hlayout.addWidget(AddRemoveButton(self.osc, self.widgets, self.tabs, address))

        vlayout.addLayout(hlayout)
        vlayout.addWidget(self.tabs)

        hlayout = QHBoxLayout()
        hlayout.addWidget(MidiLoadButton(self.osc, self.widgets, self.tabs))
        hlayout.addWidget(MidiSaveButton(self.osc))
        vlayout.addLayout(hlayout)

        self.setLayout(vlayout)
        self.setMinimumSize(930, 380)

class AddRemoveButton(QPushButton):
    def __init__(self, osc, widgets, tabs, address):
        super().__init__("Add")
        self.osc = osc
        self.widgets = widgets
        self.tabs = tabs
        self.address = address
        self.isAdd = True
        self.setEnabled(False)
        
        self.address.currentTextChanged.connect(self.updateButton)

        self.pressed.connect(self.onPressed)
        self.setFixedWidth(80)
    
    def updateButton(self, name):
        self.setEnabled(name != "")

        if getTabIndex(self.tabs, name) is None:
            self.isAdd = True
            self.setText("Add")
        else:
            self.isAdd = False
            self.setText("Remove")
    
    def onPressed(self):
        name = self.address.currentText()
        if self.isAdd:
            self.osc["serverMidi"][name] = MIDIServer(name, self.osc, self.widgets)
            newIdx = self.tabs.count()
            self.tabs.addTab(MidiPage(self.osc, self.widgets, self.tabs, name), name)
            if (self.osc["serverMidi"][name].open_ioPort()):
                self.tabs.tabBar().setTabTextColor(newIdx, QColor(0, 255, 0))

                dlg = QMessageBox(self)
                dlg.setWindowTitle("MIDI Connection")
                dlg.setText("Listening to " + name + " port")
                dlg.exec()
            else:
                self.tabs.tabBar().setTabTextColor(newIdx, QColor(255, 0, 0))

                dlg = QMessageBox(self)
                dlg.setWindowTitle("MIDI Connection")
                dlg.setText("Unable to listen to " + name + " port")
                dlg.exec()
        else:
            self.osc["serverMidi"][name].close()
            del self.osc["serverMidi"][name]
            self.tabs.removeTab(getTabIndex(self.tabs, name))

            dlg = QMessageBox(self)
            dlg.setWindowTitle("MIDI Connection")
            dlg.setText("Stopped Listening to " + name + " port")
            dlg.exec()
        
        self.updateButton(name)
        self.setDown(False)

class MidiPage(QWidget):
    def __init__(self, osc, widgets, tabs, portName):
        super().__init__()
        vlayout = QVBoxLayout()

        layout = QVBoxLayout()

        vlayout.addWidget(ReconnectButton(osc, tabs, portName))
        vlayout.addWidget(AddLineButton(osc, widgets, portName, layout))

        hlayout = QHBoxLayout()
        label = QLabel("MIDI")
        label.setFixedWidth(150)
        hlayout.addWidget(label)
        label = QLabel("Channel")
        label.setFixedWidth(50)
        hlayout.addWidget(label)
        label = QLabel("Control")
        label.setFixedWidth(50)
        hlayout.addWidget(label)
        label = QLabel()
        label.setMinimumWidth(25)
        hlayout.addWidget(label)
        label = QLabel("Command")
        label.setFixedWidth(150)
        hlayout.addWidget(label)
        label = QLabel("Page")
        label.setFixedWidth(100)
        hlayout.addWidget(label)
        label = QLabel("Index")
        label.setFixedWidth(100)
        hlayout.addWidget(label)
        label = QLabel()
        label.setFixedWidth(95)
        hlayout.addWidget(label)
        layout.addLayout(hlayout)

        # Init Layout
        for id in osc["serverMidi"][portName].getCallbacks():
            layout.addWidget(MidiPageLine(osc, widgets, portName, id))
        if len(osc["serverMidi"][portName].getCallbacks()) == 0:
            layout.addWidget(MidiPageLine(osc, widgets, portName))

        widget = QWidget()
        widget.setLayout(layout)
        scroll = QScrollArea()
        scroll.setWidget(widget)
        scroll.setWidgetResizable(True)
        vlayout.addWidget(scroll)

        self.setLayout(vlayout)

class ReconnectButton(QPushButton):
    def __init__(self, osc, tabs, portName):
        super().__init__("Reconnect to MIDI Port")
        self.osc = osc
        self.tabs = tabs
        self.portName = portName

        self.pressed.connect(self.onPressed)

    def onPressed(self):
        idx = getTabIndex(self.tabs, self.portName)
        if (self.osc["serverMidi"][self.portName].open_ioPort()):
            self.tabs.tabBar().setTabTextColor(idx, QColor(0, 255, 0))

            dlg = QMessageBox(self)
            dlg.setWindowTitle("MIDI Connection")
            dlg.setText("Reconnected to " + self.portName + " port")
            dlg.exec()
        else:
            self.tabs.tabBar().setTabTextColor(idx, QColor(255, 0, 0))

            dlg = QMessageBox(self)
            dlg.setWindowTitle("MIDI Connection")
            dlg.setText("Unable to listen to " + self.portName + " port")
            dlg.exec()

class AddLineButton(QPushButton):
    def __init__(self, osc, widgets, portName, vlayout):
        super().__init__("Add Line")
        self.osc = osc
        self.widgets = widgets
        self.portName = portName
        self.vlayout = vlayout

        self.pressed.connect(self.onPressed)

    def onPressed(self):
        self.vlayout.addWidget(MidiPageLine(self.osc, self.widgets, self.portName))

class MidiPageLine(QWidget):
    def __init__(self, osc, widgets, portName, id = None):
        super().__init__()
        self.osc = osc
        self.widgets = widgets
        self.portName = portName
        self.id = id

        self.params = {"midi": {}, "command": {}}

        hlayout = QHBoxLayout()

        self.params["midi"]["type"] = QComboBox()
        self.params["midi"]["type"].addItems(["Control Change", "Note"])
        self.params["midi"]["type"].setCurrentIndex(-1)
        self.params["midi"]["type"].setFixedWidth(150)
        self.params["midi"]["type"].currentTextChanged.connect(self.checkModified)
        hlayout.addWidget(self.params["midi"]["type"])

        self.params["midi"]["channel"] = QSpinBox()
        self.params["midi"]["channel"].setMinimum(1)
        self.params["midi"]["channel"].setMaximum(16)
        self.params["midi"]["channel"].setFixedWidth(50)
        self.params["midi"]["channel"].valueChanged.connect(self.checkModified)
        hlayout.addWidget(self.params["midi"]["channel"])

        self.params["midi"]["control"] = QSpinBox()
        self.params["midi"]["control"].setMinimum(0)
        self.params["midi"]["control"].setMaximum(127)
        self.params["midi"]["control"].setFixedWidth(50)
        self.params["midi"]["control"].valueChanged.connect(self.checkModified)
        hlayout.addWidget(self.params["midi"]["control"])
        
        spacer = QWidget()
        spacer.setMinimumWidth(1)
        hlayout.addWidget(spacer)

        self.label = QLabel("<->")
        self.label.setStyleSheet("color:grey")
        self.label.setMinimumWidth(24)
        hlayout.addWidget(self.label)

        hlayout.addWidget(QWidget())

        self.params["command"]["type"] = CommandBox(self)
        hlayout.addWidget(self.params["command"]["type"])

        self.params["command"]["page"] = PageBox(self)
        hlayout.addWidget(self.params["command"]["page"])

        self.params["command"]["index"] = QComboBox()
        self.params["command"]["index"].setEnabled(False)
        self.params["command"]["index"].setCurrentIndex(-1)
        self.params["command"]["index"].setFixedWidth(100)
        self.params["command"]["index"].currentTextChanged.connect(self.checkModified)
        hlayout.addWidget(self.params["command"]["index"])

        self.button = ConnectButton(self)
        hlayout.addWidget(self.button)

        if id is not None:
            initParams = osc["serverMidi"][portName].getCallback(id)
            self.params["midi"]["type"].setCurrentText(initParams["midi"]["type"])
            self.params["midi"]["channel"].setValue(initParams["midi"]["channel"])
            self.params["midi"]["control"].setValue(initParams["midi"]["control"])
            self.params["command"]["type"].setCurrentText(initParams["command"]["type"])
            if initParams["command"]["type"] == "Pull History":
                self.params["command"]["page"].setCurrentIndex(-1)
                self.params["command"]["index"].setCurrentIndex(-1)
            else:
                self.params["command"]["page"].setCurrentText(initParams["command"]["page"])
                self.params["command"]["index"].setCurrentText(initParams["command"]["index"])
            self.label.setStyleSheet("color:green")
            self.button.setText("Delete")

        self.setLayout(hlayout)
    
    def checkModified(self):
        if self.button.text() == "Delete":
            self.label.setStyleSheet("color:yellow")
            self.button.setText("Update")

class CommandBox(QComboBox):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        
        self.addItems(self.parent.widgets["tabs"].keys())
        self.addItem("Pull History")
        self.setCurrentIndex(-1)
        self.setFixedWidth(100)

        self.currentTextChanged.connect(self.onChange)
    
    def onChange(self, text):
        while self.parent.params["command"]["page"].itemText(0) != "":
            self.parent.params["command"]["page"].removeItem(0)
        if text == "" or text == "Pull History":
            self.parent.params["command"]["page"].setCurrentIndex(-1)
            self.parent.params["command"]["page"].setEnabled(False)
        else:
            for idx in range(0, self.parent.widgets["tabs"][text].count()):
                self.parent.params["command"]["page"].addItem(self.parent.widgets["tabs"][text].tabText(idx))
            self.parent.params["command"]["page"].addItem("CURRENT")
            self.parent.params["command"]["page"].setCurrentIndex(0)
            self.parent.params["command"]["page"].setEnabled(True)
        
        while self.parent.params["command"]["index"].itemText(0) != "":
            self.parent.params["command"]["index"].removeItem(0)
        if text == "" or text == "Pull History":
            self.parent.params["command"]["index"].setCurrentIndex(-1)
            self.parent.params["command"]["index"].setEnabled(False)
        else:
            for idx in range(0, 10 if text == "Cue" else 4):
                self.parent.params["command"]["index"].addItem(str(idx + 1))
            self.parent.params["command"]["index"].setCurrentIndex(0)
            self.parent.params["command"]["index"].setEnabled(True)
        
        self.parent.checkModified()

class PageBox(QComboBox):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        
        self.setEnabled(False)
        self.setCurrentIndex(-1)
        self.setFixedWidth(150)

        self.currentTextChanged.connect(self.onChange)
    
    def onChange(self, text):
        if text == "CURRENT":
            self.parent.params["command"]["index"].addItem("Next Page")
            self.parent.params["command"]["index"].addItem("Prev Page")
        else:
            idx = 0
            while self.parent.params["command"]["index"].itemText(idx) != "":
                if self.parent.params["command"]["index"].itemText(idx) in ["Next Page", "Prev Page"]:
                    self.parent.params["command"]["index"].removeItem(idx)
                else:
                    idx = idx + 1
        
        self.parent.checkModified()

class ConnectButton(QPushButton):
    def __init__(self, parent):
        super().__init__("Connect")
        self.parent = parent
        self.setFixedWidth(100)
        self.currentParams = {"midi": {}, "command": {}}
        self.lock = OwnerLock() # Lock to make sure only first pressed is called

        self.pressed.connect(self.onPressed)
    
    def onPressed(self):
        if self.lock.acquire(uuid4()):
            if self.text() == "Delete":
                self.parent.osc["serverMidi"][self.parent.portName].removeCallback(self.parent.id)
                self.parent.id = None
                self.parent.params["midi"]["type"].setCurrentIndex(-1)
                self.parent.params["midi"]["channel"].setValue(1)
                self.parent.params["midi"]["control"].setValue(0)
                self.parent.params["command"]["type"].setCurrentIndex(-1)

                self.parent.label.setStyleSheet("color:grey")
                self.parent.button.setText("Connect")
            else:
                self.currentParams["midi"]["type"] = self.parent.params["midi"]["type"].currentText()
                self.currentParams["midi"]["channel"] = self.parent.params["midi"]["channel"].value() - 1
                self.currentParams["midi"]["control"] = self.parent.params["midi"]["control"].value()
                self.currentParams["command"]["type"] = self.parent.params["command"]["type"].currentText()
                if self.currentParams["command"]["type"] == "Pull History":
                    if "page" in self.currentParams["command"]:
                        del self.currentParams["command"]["page"]
                    if "index" in self.currentParams["command"]:
                        del self.currentParams["command"]["index"]
                else:
                    self.currentParams["command"]["page"] = self.parent.params["command"]["page"].currentText()
                    self.currentParams["command"]["index"] = self.parent.params["command"]["index"].currentText()

                if self.text() == "Connect":
                    self.parent.id = self.parent.osc["serverMidi"][self.parent.portName].addCallback(self.currentParams.copy())
                else:
                    self.parent.osc["serverMidi"][self.parent.portName].editCallback(self.parent.id, self.currentParams.copy())
                
                self.parent.label.setStyleSheet("color:green")
                self.parent.button.setText("Delete")

        self.setDown(False)

def getTabIndex(tabs, name):
    for idx in range(0, tabs.count()):
        if name == tabs.tabText(idx):
            return idx
    return None

class MidiLoadButton(QPushButton):
    def __init__(self, osc, widgets, tabs):
        super().__init__("Load MIDI Config")
        self.osc = osc
        self.widgets = widgets
        self.tabs = tabs
        self.pressed.connect(self.clicked)
    
    def clicked(self):
        dlg = QFileDialog()
        dlg.setWindowTitle("Load MIDI Config")
        dlg.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        dlg.setDirectory("data")
        dlg.setNameFilter("*.midi")
        if dlg.exec():
            with open(dlg.selectedFiles()[0]) as file:
                loadMidi(file, self.osc, self.widgets)
            initTabs(self.osc, self.widgets, self.tabs)
        
        self.setDown(False)

class MidiSaveButton(QPushButton):
    def __init__(self, osc):
        super().__init__("Save MIDI Config")
        self.osc = osc
        self.pressed.connect(self.clicked)
    
    def clicked(self):
        nextSun = (date.today() + timedelta(6 - date.today().weekday())).strftime("%Y%m%d")

        dlg = QFileDialog()
        dlg.setWindowTitle("Save MIDI Config")
        dlg.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dlg.setDirectory("data")
        dlg.selectFile(nextSun + "_SWS.midi")
        dlg.setDefaultSuffix(".midi") 
        if dlg.exec():
            with open(dlg.selectedFiles()[0], "w") as file:
                saveMidi(file, self.osc)
        
        self.setDown(False)

def loadMidi(file, osc, widgets):
    if "serverMidi" in osc:
        for portName in osc["serverMidi"]:
            osc["serverMidi"][portName].close()
    
    osc["serverMidi"] = {}

    portName = None
    file.readline() # Skip Header Line
    while (line := file.readline().strip()):
        components = line.split("\t")
        if components[0] != portName:
            portName = components[0]
            osc["serverMidi"][portName] = MIDIServer(portName, osc, widgets)
            osc["serverMidi"][portName].open_ioPort()
        param = {
            "midi": {"type": components[1], "channel": int(components[2]), "control": int(components[3])},
            "command": {"type": components[4], "page": components[5], "index": components[6]}
        }
        osc["serverMidi"][portName].addCallback(param)

def saveMidi(file, osc):
    file.write("v1.0")
    for portName in osc["serverMidi"]:
        callbacks = osc["serverMidi"][portName].getCallbacks()
        for id in callbacks:
            file.write("\n" + portName 
                + "\t" + callbacks[id]["midi"]["type"] + "\t" + str(callbacks[id]["midi"]["channel"]) + "\t" + str(callbacks[id]["midi"]["control"])
                + "\t" + callbacks[id]["command"]["type"] + "\t" + callbacks[id]["command"]["page"] + "\t" + callbacks[id]["command"]["index"]
            )

def initTabs(osc, widgets, tabs):
    while(tabs.count() > 0):
        tabs.removeTab(0)

    for idx, name in enumerate(osc["serverMidi"]):
        tabs.addTab(MidiPage(osc, widgets, tabs, name), name)
        if (osc["serverMidi"][name].connected()):
            tabs.tabBar().setTabTextColor(idx, QColor(0, 255, 0))
        else:
            tabs.tabBar().setTabTextColor(idx, QColor(255, 0, 0))