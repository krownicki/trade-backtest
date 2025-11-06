import backtrader as bt

class SuperTrend(bt.Indicator):
    """
    SuperTrend Indicator
    """
    plotinfo = dict(subplot=False) # Plot on the main price chart
    lines = ('supertrend',) # Define the single output line
    params = (('period', 10), ('multiplier', 3.0),) # Customizable parameters

    def __init__(self):
        # ATR and Median Price are needed for the calculation
        self.atr = bt.indicators.AverageTrueRange(period=self.p.period)
        self.median_price = (self.data.high + self.data.low) / 2.0

        # These bands are dynamic based on ATR and median price
        self.basic_upper_band = self.median_price + (self.p.multiplier * self.atr)
        self.basic_lower_band = self.median_price - (self.p.multiplier * self.atr)

    def next(self):
        # On the first bar, initialize SuperTrend with the close price
        if len(self) == 1:
            self.lines.supertrend[0] = self.data.close[0]
            return

        prev_st = self.lines.supertrend[-1]
        prev_close = self.data.close[-1]

        # --- Calculate the current SuperTrend value ---
        # If the previous trend was UP (previous close > previous SuperTrend)
        if prev_close > prev_st:
            # The new ST is the max of the previous ST and the current lower band
            self.lines.supertrend[0] = max(self.basic_lower_band[0], prev_st)
        else: # If the previous trend was DOWN
            # The new ST is the min of the previous ST and the current upper band
            self.lines.supertrend[0] = min(self.basic_upper_band[0], prev_st)

        # --- Check for a flip in the trend and adjust the SuperTrend line ---
        current_close = self.data.close[0]
        if current_close > self.lines.supertrend[0]: # If price is now above the ST line
            # We are in an uptrend, so the ST line should be based on the lower band
            self.lines.supertrend[0] = self.basic_lower_band[0]
        elif current_close < self.lines.supertrend[0]: # If price is now below the ST line
            # We are in a downtrend, so the ST line should be based on the upper band
            self.lines.supertrend[0] = self.basic_upper_band[0]