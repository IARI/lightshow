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
from wrapt import synchronized
from time import sleep
import re

# List of pairs (regexp, handler)
handlers = []


def handler_for(regexp, wait, *types):
    # @decorator()
    # def gethandler(f, self, args, kwargs):
    def gethandler(f):
        handlers.append((re.compile(regexp), f, wait, types))
        return f

    return gethandler


class Program(Thread):
    def __init__(self, data, router, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stopped = Event()
        self.router = router
        self.setDaemon(True)
        self.resetProgramData(data)

    def stop(self):
        self._stopped.set()

    @property
    def length(self):
        return len(self.data)

    @synchronized
    def resetProgramData(self, data):
        self.data = data
        self.current = 0
        self.delay = FreifunkRouter.SIGNAL_DELAY

    def run(self):
        while not self._stopped.isSet():
            self.oneStep()

    @synchronized
    def oneStep(self):
        self.current %= self.length
        try:
            self.eval(self.data[self.current])
        except Exception as e:
            print('error in program: ' + str(e))
        self.current += 1
        if self.current == self.length:
            print('program terminated naturally')
            self.stop()

    def eval(self, command):
        for pattern, f, wait, types in handlers:
            m = re.match(pattern, command)
            if m:
                args = [t(s) for t, s in zip(types, m.groups())]
                f(self, *args)
                if wait:
                    sleep(self.delay)
                return
        raise Exception("Command {} could not be interpreted".format(command))

    @handler_for("(\d+)$", True, int)
    def toggle(self, lid):
        self.router[lid] = int(not self.router[lid])

    @handler_for("\+(\d+)$", True, int)
    def enable(self, lid):
        self.router[lid] = 1

    @handler_for("\-(\d+)$", True, int)
    def disable(self, lid):
        self.router[lid] = 0

    @handler_for("(\d+(,\d+)+)$", False, str)
    def para(self, ls):
        for c in ls.split(','):
            self.eval(c)

    @handler_for("d(\d+(\.\d+)?)$", False, float)
    def setDelay(self, d):
        self.delay = max(d, FreifunkRouter.SIGNAL_DELAY)

    @handler_for("g(\d+)$", False, int)
    def setPC(self, pc):
        self.current = pc - 1

    @handler_for("c(\d+)-(\d+)$", False, int, int)
    def cond(self, lid, pc):
        if not self.router[lid]:
            self.setPC(pc)

    @handler_for("t([a-zA-Z0-9]+)$", True, str)
    def setPC(self, text):
        print(text)

    @handler_for("x$", False)
    def exit(self):
        print('program terminated with x')
        self.stop()

    @handler_for("$", True)
    def empty(self):
        print('Empty program is boring!')


class Gui(QMainWindow, Ui_MainWindow):
    # default path for led directories are
    DEFAULT_PATH = '/sys/devices/platform/leds-gpio/leds/'

    def __init__(self):
        QObject.__init__(self)
        super(Gui, self).__init__()
        self.setupUi(self)
        self.show()

        # noinspection PyUnresolvedReferences
        self.list_leds.itemSelectionChanged.connect(self.selection_changed)

        self.settings = QSettings('light_show', 'router')
        self.input_routerip.setText(self.settings.value('address', ""))
        self.input_user.setText(self.settings.value('user', 'root'))
        self.input_path.setText(self.settings.value('path', Gui.DEFAULT_PATH))
        self.edt_script.setPlainText(self.settings.value('prog', ''))

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
        try:
            self.program.stop()
        except:
            pass
        self.program = Program(self.readProgram(), self.router)
        self.program.start()
        print('program started')

    def readProgram(self):
        l_progs = re.split("[\r\n]+", self.edt_script.toPlainText().strip())
        l_prog = re.split("[\s]+", l_progs[0])
        print(l_prog)
        return l_prog

    def cursorChanged(self):
        l_prog = self.readProgram()
        self.program.resetProgramData(l_prog)

    def stopProgram(self):
        if self.program and self.program.isAlive:
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
        user = self.input_user.text()
        password = self.input_password.text()
        path = self.input_path.text()
        self.router.connect(address, user or "root", password, path)

    def closeEvent(self, event):
        self.stopProgram()
        self.router.disconnect()
        self.settings.setValue('address', self.input_routerip.text())
        self.settings.setValue('user', self.input_user.text())
        # self.settings.setValue('password', self.input_user.text())
        self.settings.setValue('path', self.input_path.text())
        self.settings.setValue('prog', self.edt_script.toPlainText())
