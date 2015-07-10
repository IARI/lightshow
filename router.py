from pxssh import pxssh
from PyQt5.QtCore import QObject, pyqtSignal
import time
import logging
import re
from threading import Thread, Event, Timer
from wrapt import synchronized, decorator

logging.basicConfig(level=logging.DEBUG,
                    format='(%(threadName)-9s) %(message)s', )


def connection_demon(delay=0):
    @decorator
    def wrapper(wrapped, self, args, kwargs):
        while self._connected.wait():
            wrapped(*args, **kwargs)
            time.sleep(delay)

    return wrapper


class FreifunkRouter(QObject):
    # delay between signals on led-toggles sent to the router on a channel
    SIGNAL_DELAY = 0.25
    # path where the led directories are
    LED_PATH = "/sys/devices/platform/leds-gpio/leds/"
    # emitted when connection status to router changes
    connection_changed = pyqtSignal(str)
    # emitted when led-values change
    model_changed = pyqtSignal()

    def __init__(self, guard=False):
        QObject.__init__(self)
        self.ssh = pxssh()
        self.guard = guard
        self.leds = []
        self.goal_state = []
        self.read_state = []
        self._modelChanged = Event()
        self._channelEvents = {}
        self._lastServer = None
        self._connected = Event()

        status_reader = Thread(name="read daemon",
                               target=self._read_router_status)
        status_reader.setDaemon(True)
        status_reader.start()

        status_writer = Thread(name="write daemon",
                               target=self._write_router_status)
        status_writer.setDaemon(True)
        status_writer.start()

    @property
    def connected(self):
        try:
            self.ssh.sync_original_prompt()
            return self._lastServer
        except Exception as e:
            print('No connection\n', e)
            self._connected.clear()
            return None

    @synchronized
    def connect(self, address, user="root"):
        connected = self.connected
        if connected == address:
            print('already connected to {}'.format(connected))
            return
        elif connected:
            self.disconnect()

        self.ssh = pxssh()
        print('logging in at {} as {}'.format(address, user))
        try:
            r = self.ssh.login(address, user)
        except Exception as e:
            print("SSH session failed.\nError Message:\n", e)
            return False
        if not r:
            print("SSH session failed on login.")
            print(str(self.ssh))
        else:
            self.ssh.setwinsize(400, 400)
            self.ssh.prompt()
            self._connected.set()
            self._lastServer = address
            print("SSH session login successful")
            self.ssh.sendline('cd {}'.format(self.LED_PATH))
            self.ssh.prompt()
            self.ssh.sendline('uptime')
            self.ssh.prompt()  # match the prompt
            print(self.ssh.before)  # print everything before the prompt.
            self.setup_leds()
            self.read_router_status()
            self.connection_changed.emit(address)
        return r

    def setup_leds(self):
        command = "ls -x --color=never"
        pattern = 'never\s*(.*)'
        r = self.read_command(pattern, command)[0].strip()
        l = re.split('\s*', r)
        self.leds = [(led.split(':')[-1], led) for led in l]

    def disconnect(self):
        try:
            self.ssh.logout()
            print('logged out from {}'.format(self._lastServer))
            self.connection_changed.emit(None)
        except:
            pass

    def __del__(self):
        self.disconnect()

    @connection_demon()
    def _write_router_status(self):
        self._modelChanged.wait()
        with synchronized(self):
            def neq(i, v):
                s = self.read_state
                return len(s) > i and v != s[i]

            diff = [(i, v) for i, v in enumerate(self.goal_state) if neq(i, v)]
            sends = diff
            try:
                for i, v in sends:
                    self.read_state[i] = v
                self.send_set_items(sends)
            except OSError:
                self._connected.clear()
            except Exception as e:
                print(e)
            self._modelChanged.clear()

    @connection_demon(1)
    def _read_router_status(self):
        try:
            v = self.read_router_status()
            if self.read_state != v:
                self.read_state = v
                print('read_state changed from {} to {}'.
                      format(self.read_state, v))
                if not self.guard:
                    self.goal_state[:] = v
                    self.model_changed.emit()
        except OSError:
            self._connected.clear()
        except Exception as e:
            print(e)

    def read_router_status(self):
        c = self.read_led_values_command
        r = self.read_command("\r\n(.*)", c)[0].strip().split("\r\n")
        return list(map(int, r))

    @staticmethod
    def command_wrapper(*commands):
        return " ; ".join(commands)

    def get_led_value_command(self, nr):
        return "cat {}/brightness".format(self.leds[nr][1])

    @property
    def read_led_values_command(self):
        cs = [self.get_led_value_command(i) for i in range(len(self.leds))]
        return self.command_wrapper(*cs)

    def set_led_value_command(self, nr, brightness):
        return "echo {:d} > {}/brightness ".format(
            brightness, self.leds[nr][1])

    @synchronized
    def send_set_items(self, pairs):
        cs = map(self.set_led_value_command, *zip(*pairs))
        command = self.command_wrapper(*cs)
        self.ssh.sendline(command)
        self.ssh.prompt()

    @synchronized
    def read_command(self, pattern, *commands):
        cs = self.command_wrapper(*commands)
        self.ssh.sendline(cs)
        self.ssh.prompt()
        text = self.ssh.before.decode()
        m = re.search(pattern, text, re.M | re.S)
        if m is None:
            raise Exception('could not find "{}" in "{}"'
                            .format(pattern, text))
        return m.groups()

    def reset_channel(self, nr):
        e = self._channelEvents[nr]
        e.clear()
        Timer(self.SIGNAL_DELAY, e.set)

    @property
    def settable_channels(self):
        return [i for i, c in self._channelEvents.items() if c.isSet()]

    def __getitem__(self, nr):
        return self.goal_state.__getitem__(nr)

    def __setitem__(self, nr, brightness):
        if brightness != self.goal_state.__getitem__(nr):
            # print("change: index:{}   to brightness {}".format(nr, brightness))
            # self.read_state[:] = self.goal_state
            self.goal_state.__setitem__(nr, brightness)
            self._modelChanged.set()
