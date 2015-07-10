"""
Gui
"""
from PyQt5.QtWidgets import (QMainWindow, QListWidgetItem)

# QWidget, QFileDialog, QAction,
# QActionGroup, QMessageBox, QApplication

from PyQt5.QtCore import QObject, QSettings  # , Qt
from PyQt5.QtGui import QIcon
from gui_ui import Ui_MainWindow
from router import FreifunkRouter
from threading import Thread, Event
from wrapt import decorator
from functools import partial
from time import sleep
import re

# List of pairs (regexp, handler)
handlers = []


def handler_for(regexp, *types):
    # @decorator()
    # def gethandler(f, self, args, kwargs):
    def gethandler(f):
        handlers.append((re.compile(regexp), f, types))
        return f

    return gethandler


class Program(Thread):
    def __init__(self, data, router, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = data
        self.current = 0
        self._stopped = Event()
        self.router = router
        self.setDaemon(True)
        self.handlers = []
        self.delay = FreifunkRouter.SIGNAL_DELAY

    def stop(self):
        self._stopped.set()

    def run(self):
        while not self._stopped.isSet():
            self.current %= len(self.data)
            try:
                self.eval(self.data[self.current])
            except Exception as e:
                print('error in program: ' + str(e))
            sleep(self.delay)
            self.current += 1

    def eval(self, command):
        for pattern, f, types in handlers:
            m = re.match(pattern, command)
            if m:
                args = [t(s) for t, s in zip(types, m.groups())]
                f(self, *args)
                return
        raise Exception("Command {} could not be interpreted".format(command))

    @handler_for("(\d+)$", int)
    def toggle(self, lid):
        self.router[lid] = int(not self.router[lid])

    @handler_for("\+(\d+)$", int)
    def enable(self, lid):
        self.router[lid] = 1

    @handler_for("\-(\d+)$", int)
    def disable(self, lid):
        self.router[lid] = 0

    @handler_for("(\d+(,\d+)+)$", str)
    def para(self, ls):
        for c in ls.split(','):
            self.eval(c)

    @handler_for("$")
    def empty(self):
        print('Empty program is boring!')


class Gui(QMainWindow, Ui_MainWindow):
    # LED_AMOUNT = 4

    def __init__(self):
        QObject.__init__(self)
        super(Gui, self).__init__()
        self.setupUi(self)
        self.show()

        # noinspection PyUnresolvedReferences
        self.list_leds.itemSelectionChanged.connect(self.selection_changed)

        self.settings = QSettings('light_show', 'router')
        self.input_routerip.setText(self.settings.value('address', ""))

        self.router = FreifunkRouter()
        self.router.connection_changed.connect(self.connection_event)
        self.router.model_changed.connect(self.update_selection)

        self.connection_event(None)

        self.program = None

        # noinspection PyUnresolvedReferences
        self.btn_run.clicked.connect(self.runProgram)
        # noinspection PyUnresolvedReferences
        self.btn_stop.clicked.connect(self.stopProgram)

        # noinspection PyUnresolvedReferences
        self.btn_connect.clicked.connect(self.connect)
        # noinspection PyUnresolvedReferences
        self.btn_all.clicked.connect(self.list_leds.selectAll)
        # noinspection PyUnresolvedReferences
        self.btn_none.clicked.connect(self.list_leds.clearSelection)

    def runProgram(self):
        l_prog = re.split("\s", self.edt_script.toPlainText().strip())
        print(l_prog)
        self.program = Program(l_prog, self.router)
        self.program.start()
        print('program started')

    def stopProgram(self):
        try:
            self.program.stop()
            print('program stopped')
        except:
            print("program can't be stopped")

    @property
    def all_led_list_items(self):
        return map(self.list_leds.item, range(self.list_leds.count()))

    def connection_event(self, connected):
        connected = bool(connected)
        color = 'green' if connected else 'red'
        self.btn_connect.setIcon(QIcon(":/icons/icons/{}.png".format(color)))
        self.frame_upper.setEnabled(connected)
        if connected:
            self.make_led_list()

    def make_led_list(self):
        self.list_leds.clear()
        for name, path in self.router.leds:
            this_item = QListWidgetItem(name)
            # this_item.setFlags(this_item.flags() | Qt.ItemIsEditable)
            self.list_leds.addItem(this_item)

    def update_selection(self):
        self.list_leds.blockSignals(True)
        for i, v in zip(self.all_led_list_items, self.router[:]):
            i.setSelected(bool(v))
        self.list_leds.blockSignals(False)

    def selection_changed(self):
        items = self.all_led_list_items
        self.router[:] = [int(i.isSelected()) for i in items]

    def connect(self):
        address = self.input_routerip.text()
        self.router.connect(address)

    def closeEvent(self, event):
        self.stopProgram()
        self.router.disconnect()
        self.settings.setValue('address', self.input_routerip.text())
