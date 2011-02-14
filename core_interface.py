import jsonrpc
from jsonrpc.proxy import JSONRPCException

class CoreInterface:
    def __init__(self):
        self.access = jsonrpc.ServiceProxy('http://user:pass@127.0.0.1:8332')

    def transactions(self):
        return self.access.listtransactions()

    def balance(self):
        return self.access.getbalance()

    def stop(self):
        return self.access.stop()

    def validate_address(self, address):
        return self.access.validateaddress(address)['isvalid']

    def send(self, address, amount):
        return self.access.sendtoaddress(address, amount)

    def default_address(self):
        return self.access.getaccountaddress('')

    def new_address(self):
        return self.access.getnewaddress('')
    
    def is_initialised(self):
        return self.access.isinitialized()

