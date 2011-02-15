from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtWebKit import *
import send

class FocusLineEdit(QLineEdit):
    def __init__(self, text):
        super(FocusLineEdit, self).__init__(text)
        self.setReadOnly(True)
        self.setMaxLength(40)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setCursorPosition(100)
            self.selectAll()
            event.accept()
        else:
            super(FocusLineEdit, self).mousePressEvent(event)

    def focusOutEvent(self, event):
        event.accept()

    def sizeHint(self):
        sizeh = super(FocusLineEdit, self).sizeHint()
        sizeh.setWidth(self.fontMetrics().averageCharWidth() * self.maxLength())
        return sizeh

class TransactionItem(QTableWidgetItem):
    def __init__(self, text, align=Qt.AlignLeft):
        super(TransactionItem, self).__init__(text)
        self.setFlags(Qt.ItemIsEnabled)
        self.setTextAlignment(align|Qt.AlignVCenter)

class TransactionsTable(QTableWidget):
    # These are the proportions for the various columns
    hedprops = (130, 150, 400, 100, 100)

    def __init__(self):
        super(TransactionsTable, self).__init__()

        self.setColumnCount(5)
        hedlabels = (self.tr('Status'),
                     self.tr('Date'),
                     self.tr('Transactions'),
                     self.tr('Credits'),
                     self.tr('Balance'))
        self.setHorizontalHeaderLabels(hedlabels)
        for i, sz in enumerate(self.hedprops):
            self.horizontalHeader().resizeSection(i, sz)

        self.setSelectionBehavior(self.SelectRows)
        self.setSelectionMode(self.NoSelection)
        self.setFocusPolicy(Qt.NoFocus)
        self.setAlternatingRowColors(True)
        self.verticalHeader().hide()
        self.setShowGrid(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.horizontalHeader().setStretchLastSection(True)

    # Resize columns while maintaining proportions
    def resizeEvent(self, event):
        self_width = event.size().width()
        total_prop_width = sum(self.hedprops)
        newszs = [sz * self_width / total_prop_width for sz in self.hedprops]
        for i, sz in enumerate(newszs):
            self.horizontalHeader().resizeSection(i, sz)

    def add_transaction_entry(self, transaction):
        self.insertRow(0)
        confirms = transaction['confirmations']
        unixtime = transaction['time']
        if 'address' in transaction:
            address = transaction['address']
        credit =  transaction['amount']
        balance = 'N/A'
        category = transaction['category']

        row_disabled = False
        if confirms > 5:
            status = self.tr('Confirmed (%i)')%confirms
        elif confirms > 1:
            status = self.tr('Processing... (%i)')%confirms
        else:
            status = self.tr('Validating... (%i)')%confirms
            row_disabled = True
        status_item = TransactionItem(status)
        self.setItem(0, 0, status_item)

        date_formatter = QDateTime()
        date_formatter.setTime_t(unixtime)
        # we need to do this in parts to have a month name translation
        # datetime = date_formatter.toString('hh:mm d ')
        # datetime += self.tr(date_formatter.toString('MMM '))
        # datetime += date_formatter.toString('yy')
        datetime = date_formatter.toString('hh:mm d MMM yy')
        date_item = TransactionItem(datetime)
        self.setItem(0, 1, date_item)

        if category == 'send':
            description = self.tr('Sent to %s')%address
        elif category == 'receive':
            description = self.tr('Received to %s')%address
        elif category == 'generate':
            description = self.tr('Generated')
        trans_item = TransactionItem(description)
        self.setItem(0, 2, trans_item)

        credits_item = TransactionItem(str(credit), Qt.AlignRight)
        self.setItem(0, 3, credits_item)

        balance_item = TransactionItem(str(balance), Qt.AlignRight)
        self.setItem(0, 4, balance_item)

        if row_disabled:
            self.disable_table_item(status_item)
            self.disable_table_item(date_item)
            self.disable_table_item(trans_item)
            self.disable_table_item(credits_item)
            self.disable_table_item(balance_item)

    def disable_table_item(self, item):
        brush = item.foreground()
        brush.setColor(Qt.gray)
        item.setForeground(brush)
        font = item.font()
        font.setStyle(font.StyleItalic)
        item.setFont(font)

class Cashier(QDialog):
    def __init__(self, core, clipboard, parent=None):
        super(Cashier, self).__init__(parent)
        self.core = core
        self.clipboard = clipboard

        self.create_actions()
        main_layout = QVBoxLayout(self)

        youraddy = QHBoxLayout()
        # Balance + Send button
        self.balance_label = QLabel()
        self.refresh_balance()
        sendbtn = QToolButton(self)
        sendbtn.setDefaultAction(self.send_act)
        # Address + New button + Copy button
        uraddtext = QLabel(self.tr('Your address:'))
        self.addy = FocusLineEdit(self.core.default_address())
        newaddybtn = QToolButton(self)
        newaddybtn.setDefaultAction(self.newaddy_act)
        copyaddybtn = QToolButton(self)
        copyaddybtn.setDefaultAction(self.copyaddy_act)
        # Add them to the layout
        youraddy.addWidget(uraddtext)
        youraddy.addWidget(self.addy)
        youraddy.addWidget(newaddybtn)
        youraddy.addWidget(copyaddybtn)
        youraddy.addStretch()
        youraddy.addWidget(self.balance_label)
        youraddy.addWidget(sendbtn)
        main_layout.addLayout(youraddy)

        self.transactions_table = TransactionsTable()
        main_layout.addWidget(self.transactions_table)

        #webview = QWebView()
        #webview.load('http://bitcoinwatch.com/')
        #webview.setFixedSize(880, 300)
        #mf = webview.page().mainFrame()
        #mf.setScrollBarPolicy(Qt.Horizontal,
        #                      Qt.ScrollBarAlwaysOff)
        #mf.setScrollBarPolicy(Qt.Vertical,
        #                      Qt.ScrollBarAlwaysOff)
        #main_layout.addWidget(webview)

        self.setWindowTitle(self.tr('Spesmilo'))
        if parent is not None:
            self.setWindowIcon(parent.bitcoin_icon)
        self.setAttribute(Qt.WA_DeleteOnClose, False)

        refresh_info_timer = QTimer(self)
        refresh_info_timer.timeout.connect(self.refresh_info)
        refresh_info_timer.start(1000)
        # Stores time of last transaction added to the table
        self.last_tx_time = 0
        # Used for updating number of confirms
        #   key=txid, category  val=row, confirms
        self.trans_lookup = {}
        self.refresh_info()
        #self.transactions_table.add_transaction_entry({'confirmations': 3, 'time': 1223332, 'address': 'fake', 'amount': 111, 'category': 'send'})
        #self.transactions_table.add_transaction_entry({'confirmations': 0, 'time': 1223332, 'address': 'fake', 'amount': 111, 'category': 'send'})

        self.resize(900, 300)

    def refresh_info(self):
        self.refresh_balance()
        self.refresh_transactions()

    def refresh_transactions(self):
        #transactions = [t for t in self.core.transactions() if t['time'] > self.last_tx_time]
        transactions = self.core.transactions()
        self.transactions_table.clearContents()
        self.transactions_table.setRowCount(0)
        # whether list has updates
        #if not transactions:
        #    return
        #self.last_tx_time = transactions[-1]['time']
        transactions.sort(key=lambda t: t['time'])

        #txids = [t['txid'] for t in transactions]
        # remove duplicates
        #txids = list(set(txids))
        #for txid in txids:
        #    mattrans = [t for t in transactions if t['txid'] == txid]

        for t in transactions:
            self.transactions_table.add_transaction_entry(t)

    def refresh_balance(self):
        bltext = self.tr('Balance: %.2f BTC')%self.core.balance()
        self.balance_label.setText(bltext)

    def create_actions(self):
        icon = lambda s: QIcon('./icons/' + s)

        self.send_act = QAction(icon('forward.png'), self.tr('Send'),
            self, toolTip=self.tr('Send bitcoins to another person'),
            triggered=self.new_send_dialog)
        self.newaddy_act = QAction(icon('document_new.png'),
            self.tr('New address'), self,
            toolTip=self.tr('Create new address for accepting bitcoins'),
            triggered=self.new_address)
        self.copyaddy_act = QAction(icon('klipper.png'),
            self.tr('Copy address'),
            self, toolTip=self.tr('Copy address to clipboard'),
            triggered=self.copy_address)

    def new_send_dialog(self):
        if self.parent() is not None:
            send_dialog = send.SendDialog(self.core, self.parent())
        else:
            send_dialog = send.SendDialog(self.core, self)

    def new_address(self):
        self.addy.setText(self.core.new_address())

    def copy_address(self):
        self.clipboard.setText(self.addy.text())

if __name__ == '__main__':
    import os
    import sys
    import core_interface
    os.system('/home/genjix/src/bitcoin/bitcoind')
    translator = QTranslator()
    #translator.load('data/translations/eo_EO')
    app = QApplication(sys.argv)
    core = core_interface.CoreInterface()
    clipboard = qApp.clipboard()
    cashier = Cashier(core, clipboard)
    cashier.show()
    sys.exit(app.exec_())
