import sys
from PyQt5.QtWidgets import QApplication
from gui import Gui

app = QApplication(sys.argv)
gui = Gui()

app.exec_()
