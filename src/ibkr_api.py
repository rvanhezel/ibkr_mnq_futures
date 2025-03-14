import threading
import time
import queue
from ibapi.client import EClient
from ibapi.wrapper import EWrapper



class IBConnection(EWrapper, EClient):
    
    def __init__(self, host, port, client_id):
        EClient.__init__(self, self)
        self.host = host
        self.port = port
        self.client_id = client_id

        self.next_order_id = None
        self.connected = False

    def connect(self):
        """Connect to Interactive Brokers TWS/Gateway"""
        try:
            super().connect(self.host, self.port, self.client_id)
            thread = threading.Thread(target=self.run)
            thread.start()
            
            # Wait for nextValidId to ensure connection is established
            timeout = 10
            while self.next_order_id is None and timeout > 0:
                time.sleep(0.1)
                timeout -= 0.1
                
            self.connected = self.next_order_id is not None
            if self.connected:
                print("Successfully connected to Interactive Brokers")
            else:
                print("Failed to connect to Interactive Brokers")
                
        except Exception as e:
            print(f"Error connecting to Interactive Brokers: {str(e)}")
            self.connected = False

    def nextValidId(self, orderId: int):
        """Callback for next valid order ID"""
        print("nextValidId called")
        self.next_order_id = orderId

    def disconnect(self):
        """Disconnect from Interactive Brokers"""
        if self.connected:
            self.done = True
            super().disconnect()
            self.connected = False
            print("Disconnected from Interactive Brokers")

    def error(self, req_id, error_code, error_message, misc):
        if error_code in [2103, 2104, 2105, 2106, 2119, 2158]:
            print(f"({error_code}) {error_message} {misc}")
        else:
            raise Exception(f"Error: {req_id} {error_code} {error_message} {misc}")
        
    def historicalData(self, req_id, bar):
        print(f"Data received: {req_id} - {bar.date} - {bar.close}")

    def historicalDataEnd(self, reqId, start, end):
        print(f"historicalDataEnd - Historical data request completed - {reqId} `- {start} - {end}")

    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        print(f"Order Status: {orderId} - {status} - {filled} - {remaining} - {avgFillPrice} - {lastFillPrice} - {mktCapPrice}")

