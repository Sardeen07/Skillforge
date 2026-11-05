import threading
import time


class Account:
    def __init__(self, id, balance):
        self.id, self.balance, self.lock = id, balance, threading.Lock()


def transfer(src, dst, amount):
    with src.lock:
        time.sleep(0)  # yield, as a real database call would
        with dst.lock:
            src.balance -= amount
            dst.balance += amount
