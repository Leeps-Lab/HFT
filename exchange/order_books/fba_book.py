from exchange.order_books.book_price_q import BookPriceQ
from exchange.order_books.list_elements import SortedIndexedDefaultList
import heapq
import math
import logging as log

MIN_BID = 0
MAX_ASK = 2000000000

def merge(ait, bit, key):
    a=None
    b=None
    try:
        a = next(ait)
    except StopIteration:
        yield from bit
        return
    if a is not None:
        try:
            b = next(bit)
        except StopIteration:
            yield from ait
            return

        while b is not None:
            try:
                try:
                    while(key(a) <= key(b)):
                        yield a
                        a = next(ait)
                except StopIteration:
                    yield from bit
                    return

                yield b
                b = next(bit)
            except StopIteration:
                yield from ait 
                return

class FBABook:
    def __init__(self):
        self.bids = SortedIndexedDefaultList(index_func = lambda bq: bq.price, 
                            initializer = lambda p: BookPriceQ(p),
                            index_multiplier = -1)
        self.asks = SortedIndexedDefaultList(index_func = lambda bq: bq.price, 
                            initializer = lambda p: BookPriceQ(p))

    def __str__(self):
        return """
  Bids:
{}

  Asks:
{}""".format(self.bids, self.asks)


    def cancel_order(self, id, price, volume, buy_sell_indicator):
        '''
        Cancel all or part of an order. Volume refers to the desired remaining shares to be executed: if it is 0, the order is
        fully cancelled, otherwise an order of volume volume remains.
        '''
        orders = self.bids if buy_sell_indicator == b'B' else self.asks
        
        if price not in orders or id not in orders[price].order_q:
            log.debug('No order in the book to cancel, cancel ignored.')
            return []
        else:
            amount_canceled=0
            current_volume=orders[price].order_q[id]
            if volume==0:                                       #fully cancel
                orders[price].cancel_order(id)
                amount_canceled = current_volume
                if orders[price].interest == 0:
                    orders.remove(price)
            elif volume < current_volume:
                orders[price].reduce_order(id, volume)      
                amount_canceled = current_volume - volume
            else:
                amount_canceled = 0

            return [(id, amount_canceled)]

    def enter_buy(self, id, price, volume, enter_into_book = True):
        '''
        Enter a limit order to buy at price price: do NOT try and match
        '''
        if enter_into_book:
            self.bids[price].add_order(id, volume)
            entered_order = (id, price, volume)
            return ([], entered_order)
        else:
            return ([], None)

    def enter_sell(self, id, price, volume, enter_into_book):
        '''
        Enter a limit order to sell at price price: do NOT try and match
        '''
        if enter_into_book:
            self.asks[price].add_order(id, volume)
            entered_order = (id, price, volume)
            return ([], entered_order) 
        else:
            return ([], None)

    def batch_process(self):
        log.debug('Running batch auction..')
        log.debug('Order book=%s', self)
        asks_volume = sum([price_book.interest for price_book in self.asks.ascending_items()])
        all_orders_descending = merge(
            self.asks.descending_items(),
            self.bids.ascending_items(), 
            key= lambda bpq: -bpq.price)
        log.debug('Ask prices=%s:%s, bid prices=%s:%s', 
            [(p.price, p.interest) for p in self.asks.ascending_items()], 
            [(p.price, p.interest) for p in self.asks.ascending_items()],
            [(p.price, p.interest) for p in self.bids.ascending_items()],
            [(p.price, p.interest) for p in self.bids.descending_items()])
        assert len([p.price for p in self.asks.descending_items()])==len([p.price for p in self.asks.ascending_items()]) 
        
        orders_volume = prior_orders_volume = 0
        clearing_price=None
        log.debug('Calculating clearing price..')
        bpq=prior_bpq=None

        for bpq in all_orders_descending:
            prior_orders_volume = orders_volume
            orders_volume += bpq.interest
            if orders_volume > asks_volume:
                break
            prior_bpq=bpq
        #If prior_orders_volume exactly hit asks and loop was able to continue, price is averaged, otherwise its the first price that pushed over limit.
        if prior_orders_volume==asks_volume and prior_bpq is not None:
            clearing_price = math.ceil((prior_bpq.price+bpq.price)/2)
        elif orders_volume>asks_volume:
            clearing_price = bpq.price

        log.debug('Clearing price: %s', clearing_price)

        matches = []
        ask_it = self.asks.ascending_items()
        if clearing_price is not None:
            try:
                ask_node = next(ask_it)
                ask_price = ask_node.price

                #iterate over bids starting with highest
                for bid_node in self.bids.ascending_items():
                    bid_price = bid_node.price
                    if bid_price<clearing_price or ask_price>clearing_price:
                        break
                    else:
                        for (bid_id, volume) in list(bid_node.order_q.items()):
                            volume_filled = 0
                            while volume_filled < volume and ask_price <= clearing_price:
                                (filled, fulfilling_orders) = ask_node.fill_order(volume-volume_filled)
                                volume_filled += filled
                                matches.extend([((bid_id, ask_id), clearing_price, volume) for (ask_id, volume) in fulfilling_orders])
                                if volume_filled < volume:
                                    self.asks.remove(ask_node.price)
                                    ask_node = next(ask_it)
                                    ask_price = ask_node.price
                            #update bid in book
                            assert volume_filled<=volume
                            if volume_filled==volume:
                                bid_node.cancel_order(bid_id)
                                if bid_node.interest == 0:
                                    self.bids.remove(bid_node.price)
                            elif volume_filled >0:
                                bid_node.reduce_order(bid_id, volume - volume_filled)
            except StopIteration:
                pass
        return matches


