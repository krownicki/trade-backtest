import backtrader as bt

from utils import SuperTrend


class SuperTrendStrategy(bt.Strategy):
    params = (
        ('st_period', 7),
        ('st_multiplier', 3.0),
        ('trail_percent', 0.03), # Trailing stop percentage
    )
    def __init__(self):
        self.order = None
        self.st = SuperTrend(self.datas[0], period=self.p.st_period, multiplier=self.p.st_multiplier)

        # State variables to manage the confirmation logic
        self.waiting_for_buy_confirmation = False
        self.waiting_for_sell_confirmation = False

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                # On buy order completion, place a trailing sell stop
                self.sell(exectype=bt.Order.StopTrail, trailpercent=self.p.trail_percent)
            elif order.issell():
                # On sell order completion, place a trailing buy stop
                self.buy(exectype=bt.Order.StopTrail, trailpercent=self.p.trail_percent)

        self.order = None # Reset order after completion or cancellation

    def next(self):
        if self.order: # If an order is pending, do nothing
            return

        # Determine current and previous trend based on SuperTrend line
        is_uptrend = self.data.close[0] > self.st.supertrend[0]
        was_uptrend = self.data.close[-1] > self.st.supertrend[-1]

        # --- Confirmation Logic ---
        # If we were waiting for a buy confirmation...
        if self.waiting_for_buy_confirmation:
            self.waiting_for_buy_confirmation = False # Reset flag
            if is_uptrend and not self.position: # Check if trend confirmed and not already in position
                self.order = self.buy()
                return

        # If we were waiting for a sell confirmation...
        if self.waiting_for_sell_confirmation:
            self.waiting_for_sell_confirmation = False # Reset flag
            if not is_uptrend and not self.position: # Check if trend confirmed and not already in position
                self.order = self.sell()
                return

        # --- Flip Detection Logic ---
        # A flip from downtrend to uptrend occurred on the previous bar
        if is_uptrend and not was_uptrend:
            # Only set the flag if not already waiting for a sell confirmation
            if not self.waiting_for_sell_confirmation:
                self.waiting_for_buy_confirmation = True

        # A flip from uptrend to downtrend occurred on the previous bar
        if not is_uptrend and was_uptrend:
            # Only set the flag if not already waiting for a buy confirmation
            if not self.waiting_for_buy_confirmation:
                self.waiting_for_sell_confirmation = True
