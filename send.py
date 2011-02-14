from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtWebKit import *

class SendDialog(QDialog):
    def __init__(self, core, parent):
        super(SendDialog, self).__init__(parent)
        self.core = core
        
        formlay = QFormLayout()
        self.destaddy = QLineEdit()
        self.amount = QLineEdit()
        self.amount.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        amount_max_width = self.fontMetrics().averageCharWidth() * 10
        self.amount.setMaximumWidth(amount_max_width)
        dv = QDoubleValidator()
        dv.setDecimals(2)
        dv.setNotation(QDoubleValidator.StandardNotation)
        self.amount.setValidator(dv)
        formlay.addRow(self.tr('Pay to:'), self.destaddy)
        amountlay = QHBoxLayout()
        amountlay.addWidget(self.amount)
        amountlay.addStretch()
        formlay.addRow(self.tr('Amount:'), amountlay)

        actionlay = QHBoxLayout()
        sendbtn = QPushButton(self.tr('&Send'))
        sendbtn.clicked.connect(self.do_payment)
        sendbtn.setAutoDefault(True)
        cancelbtn = QPushButton(self.tr('&Cancel'))
        cancelbtn.clicked.connect(self.reject)
        actionlay.addStretch()
        actionlay.addWidget(sendbtn)
        actionlay.addWidget(cancelbtn)

        # layout includes form + instructions
        instructions = QLabel(self.tr('<i>Enter a bitcoin address (e.g. 1A9Pv2PYuZYvfqku7sJxovw99Az72mZ4YH)</i>'))
        mainlay = QVBoxLayout(self)
        mainlay.addWidget(instructions)
        mainlay.addLayout(formlay)
        mainlay.addLayout(actionlay)

        if parent is not None:
            self.setWindowIcon(parent.bitcoin_icon)
        self.setWindowTitle(self.tr('Send bitcoins'))
        self.show()

    def do_payment(self):
        if not self.amount.text():
            self.amount.setFocus(Qt.OtherFocusReason)
            return
        self.hide()

        addy = self.destaddy.text()
        if not self.core.validate_address(addy):
            error = QMessageBox(QMessageBox.Critical, 
                                self.tr('Invalid address'),
                                self.tr('Invalid address: %s')%addy)
            error.exec_()
            self.reject()
            return

        amount = float(self.amount.text())
        balance = self.core.balance()
        if amount > balance:
            error = QMessageBox(QMessageBox.Critical, 
                                self.tr('Insufficient balance'),
                            self.tr('Balance of %g is too small.')%balance)
            error.exec_()
            self.reject()
            return

        self.core.send(addy, amount)
        self.accept()

if __name__ == '__main__':
    import os
    import sys
    import core_interface
    os.system('bitcoind')
    translator = QTranslator()
    #translator.load('data/translations/eo_EO')
    app = QApplication(sys.argv)
    core = core_interface.CoreInterface()
    send = SendDialog(core, None)
    sys.exit(app.exec_())
