from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtWebKit import *
import core_interface
import cashier
import send

class ConnectingDialog(QDialog):
    def __init__(self, parent):
        super(ConnectingDialog, self).__init__(parent)
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(QLabel(self.tr('Connecting...')))
        progressbar = QProgressBar()
        progressbar.setMinimum(0)
        progressbar.setMaximum(0)
        main_layout.addWidget(progressbar)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        abortbtn = QPushButton('&Abort')
        abortbtn.clicked.connect(self.stop)
        button_layout.addWidget(abortbtn)
        main_layout.addLayout(button_layout)

        if parent is not None:
            self.setWindowIcon(parent.bitcoin_icon)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.show()

    def stop(self):
        self.hide()
        self.parent().stop()

    def closeEvent(self, event):
        self.hide()
        event.ignore()

class TrayIcon(QSystemTrayIcon):
    def __init__(self, core, parent):
        super(TrayIcon, self).__init__(parent)
        self.core = core
        self.current_window = None
        self.create_menu()
        self.setIcon(self.parent().bitcoin_icon)
        self.activated.connect(self.toggle_window)
        self.show()
    
    def create_menu(self):
        tray_menu = QMenu()
        self.cash_act = QAction(self.tr('&Cashier'), self)
        self.cash_act.triggered.connect(self.show_cashier)
        self.cash_act.setDisabled(True)
        tray_menu.addAction(self.cash_act)
        self.send_act = QAction(self.tr('&Send funds'), self)
        self.send_act.triggered.connect(self.show_send)
        self.send_act.setDisabled(True)
        tray_menu.addAction(self.send_act)
        tray_menu.addSeparator()
        quit_act = QAction(self.tr('&Quit'), self)
        quit_act.triggered.connect(self.quit)
        tray_menu.addAction(quit_act)
        self.setContextMenu(tray_menu)

    def delete_window(self):
        if self.current_window is not None:
            self.current_window.deleteLater()

    def create_connecting(self):
        self.delete_window()
        self.current_window = ConnectingDialog(self.parent())

    def create_cashier(self):
        self.cash_act.setDisabled(False)
        self.send_act.setDisabled(False)
        self.delete_window()
        self.current_window = cashier.Cashier(self.core, qApp.clipboard(),
                                              self.parent())
        self.show_cashier()

    def show_cashier(self):
        self.current_window.show()

    def toggle_window(self, reason):
        if reason == self.Trigger:
            if self.current_window is not None:
                if self.current_window.isVisible():
                    self.current_window.hide()
                else:
                    self.current_window.show()

    def show_send(self):
        send.SendDialog(self.core, self.parent())

    def quit(self):
        self.parent().stop()

class RootWindow(QMainWindow):
    CLIENT_NONE = 0
    CLIENT_CONNECTING = 1
    CLIENT_DOWNLOADING = 2
    CLIENT_RUNNING = 3

    def __init__(self):
        super(RootWindow, self).__init__()
        self.core = core_interface.CoreInterface()
        icon = lambda s: QIcon('./icons/' + s)
        self.bitcoin_icon = icon('bitcoin32.xpm')
        self.tray = TrayIcon(self.core, self)

        self.state = self.CLIENT_NONE
        refresh_state_timer = QTimer(self)
        refresh_state_timer.timeout.connect(self.refresh_state)
        refresh_state_timer.start(1000)
        self.refresh_state()

    def refresh_state(self):
        if self.state == self.CLIENT_NONE:
            self.state = self.CLIENT_CONNECTING
            # show initialising dialog
            self.tray.create_connecting()
        elif self.state == self.CLIENT_CONNECTING:
            if self.core.is_initialised():
                # some voodoo here checking whether we have blocks
                self.state = self.CLIENT_RUNNING
                self.tray.create_cashier()

    def closeEvent(self, event):
        super(RootWindow, self).closeEvent(event)
        self.stop()

    def stop(self):
        try:
            # Keep looping until connected so we can issue the stop command
            while True:
                try:
                    self.core.stop()
                except core_interface.JSONRPCException:
                    pass
                except:
                    raise
                else:
                    break
        # Re-proprogate exception & trigger app exit so we can break out
        except:
            raise
        finally:
            qApp.quit()

if __name__ == '__main__':
    import os
    import sys

    os.system('bitcoind')
    app = QApplication(sys.argv)
    translator = QTranslator()
    #translator.load('il8n/eo_EO')
    app.installTranslator(translator)
    app.setQuitOnLastWindowClosed(False)
    rootwindow = RootWindow()
    sys.exit(app.exec_())

