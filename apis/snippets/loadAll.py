import os.path
import sys
import traceback
sys.path.insert(0, '../')

from apis.snippets.loadSingle import loadSingleNumSettings, runSingle
from PyQt6.QtWidgets import (
    QMessageBox,
    QPushButton,
)
from util.customWidgets import ProgressDialog

class LoadAllButton(QPushButton):
    def __init__(self, osc, filenames, personal):
        super().__init__("Load All")
        self.osc = osc
        self.filenames = filenames
        self.personal = personal
        self.pressed.connect(self.clicked)
    
    def clicked(self):
        dlg = ProgressDialog("All Settings Load", self.main)
        dlg.exec()

        self.setDown(False)
        
    def main(self, dlg):
        try:
            dlg.initBar.emit(loadAllNumSettings(self.filenames))
            for chName in self.filenames:
                if (self.filenames[chName].currentText() != ""):
                    if (os.path.exists("data/" + self.filenames[chName].currentText())):
                        runSingle(self.osc, self.filenames[chName].currentText(), True, dlg)
                        self.personal[chName].setCurrentText(self.filenames[chName].currentText().split(".")[0].split("_")[2])
                    else:
                        print("Invalid filename for " + chName)
            dlg.complete.emit()
        except Exception as ex:
            print(traceback.format_exc())
            dlg.raiseException.emit(ex)

def loadAllNumSettings(filenames):
    num = 0
    for chName in filenames:
        if (filenames[chName].currentText() != "" and os.path.exists("data/" + filenames[chName].currentText())):
            num = num + loadSingleNumSettings(filenames[chName].currentText(), True)
    return num