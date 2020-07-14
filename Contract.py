from decimal import Decimal
class Contract:
    def __init__(self, symbol, bid, ask, strikePrice, expiration):
        self.symbol = symbol
        self.bid = bid
        self.ask = ask
        self.strikePrice = strikePrice
        self.expiration = expiration

    
    def toString(self):
        print(self.symbol, " ", self.bid, " ", self.ask, " ", self.strikePrice, " ", self.expiration)
    
    ### ESTIMATE PREMIUM TO BE BETWEEN BID AND ASK 
    def premiumPrice(self):
        return Decimal(str((self.bid + self.ask) / 2))