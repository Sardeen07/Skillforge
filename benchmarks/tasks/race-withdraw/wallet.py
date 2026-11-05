import time


class InsufficientFunds(Exception):
    pass


class Wallet:
    def __init__(self, balance):
        self.balance = balance

    def withdraw(self, amount):
        if self.balance < amount:
            raise InsufficientFunds(amount)
        time.sleep(0.001)  # fraud check call
        self.balance -= amount
        return self.balance
