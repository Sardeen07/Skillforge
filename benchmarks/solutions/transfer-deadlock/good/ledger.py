import threading
import time


class Account:
    def __init__(self, id, balance):
        self.id, self.balance, self.lock = id, balance, threading.Lock()


def transfer(src, dst, amount):
    # Always lock in one global order (by account id), whichever way the money moves,
    # so two opposite transfers can never each hold the lock the other needs.
    first, second = sorted((src, dst), key=lambda acct: acct.id)
    with first.lock:
        time.sleep(0)  # yield, as a real database call would
        with second.lock:
            src.balance -= amount
            dst.balance += amount
