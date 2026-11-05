import threading
import time


class InsufficientFunds(Exception):
    pass


class Wallet:
    def __init__(self, balance):
        self.balance = balance
        self._lock = threading.Lock()

    def withdraw(self, amount):
        with self._lock:  # the check and the update must be one atomic step
            if self.balance < amount:
                raise InsufficientFunds(amount)
            time.sleep(0.001)  # fraud check call
            self.balance -= amount
            return self.balance
