import datetime as dt
import pandas as pd

class IndexModel:

    """
    Class representing the index model.
    The class stores price data and computes index attributes (such as rebalance dates, selection dates, constituents, returns and index levels)
    over time. 
    """
    def __init__(self) -> None:
        self.prices: pd.DataFrame = None 
        self.weights: list[float] = [0.5, 0.25, 0.25]
        
        self.rebalance_dates: pd.DatetimeIndex = None
        self.selection_dates: dict[pd.Timestamp, pd.Timestamp]= {}
        self.constituents: dict[pd.Timestamp, list[str]] = {}
        
        self.index_values: pd.Series = None
        self.index_returns : pd.Series = None 
        
        self.base_level: float = 100.0



    def calc_index_level(self, start_date: dt.date, end_date: dt.date) -> None:
        
        """
        self.prices denotes prices and is stored in a DataFrame. 
        """
        
        
        self.prices = (
            pd.read_csv("data_sources/stock_prices.csv", 
            parse_dates=["Date"],
            dayfirst=True
            )
            .set_index("Date")
        )
        
        

        
        
        """
        self.rebalance_dates denotes date for the first business day each month. 
        It is computed by grouping the data by month, and locating first index value of that month. 
        self.selection_dates creates a dictionary for self.rebalance_dates, the first business day of each month is mapped to 
        corresponding selection date. The selection date is the previous business day, corresponding to the last business day of the 
        previous month.
        """

        self.rebalance_dates = (
            self.prices.loc[start_date:end_date]
            .resample("BMS")
            .first()
            .index
            )
    
        

        self.selection_dates = {}
        
        for date in self.rebalance_dates:
            prev_date = self.prices.loc[self.prices.index < date].index[-1]
            self.selection_dates[date] = prev_date

        
    
        
        
        """ 
        self.constituents is a dictionary, mapping each rebalance date to its constituents. 
        It is computed by locating the stocks with the highest price per share (during selection date), and mapping 
        these stocks to the corresponding rebalance date in a list (in descending order).
        The descending order is important to ensure that the weights are allocated correctly. 

        Note: The reason that the selection solely depends on price per share is because all stocks have the same amount of stocks outstanding. 
        This means that market cap can be computed through price per share solely, since: 
        market cap = price per share * amt shares outstanding (same for all stocks).
        """

        self.constituents = {}
        
        for rebalance_date, selection_date in self.selection_dates.items(): 
            prices_on_day = self.prices.loc[selection_date]
            
            top_3 = prices_on_day.sort_values(ascending=False).head(3).index.tolist()
            
            self.constituents[rebalance_date] = top_3

        
        

        
        
        """
       self.index_returns is a Series of total returns from the index composition. 
       This dictionary is computed as below: 
       If units are None (first day of time-series), or yesterday was a rebalance date, a new composition must be created. 
       Find the latest (yesterday's) rebalance date: 
            Find which list of stocks corresponds to the constituents of the last rebalance date.
            Compute units of shares (equivalent of amount of shares that would have been purchased, if the value of the index actually had been 
            invested in specified stocks, according to the composition)
       Compute total index value and compare with previous date index value to obtain index_return. 
       Note: Because the new composition becomes effective close on the rebalance day, the new composition is implemented the day after the 
       rebalance date.
        """
        
        
        self.index_returns = {}
        

        dates = self.prices.loc[start_date:end_date].index
        current_index_value = self.base_level
        units = None

        
        for i in range(1, len(dates)):
             today = dates[i]
             yesterday = dates[i - 1]

             if units is None or yesterday in self.rebalance_dates:
                active_rebalance_date = max(
                       date for date in self.rebalance_dates if date <= yesterday
                       )
                stocks = self.constituents[active_rebalance_date]
                units = (
                    (current_index_value * pd.Series(self.weights, index=stocks))
                    / self.prices.loc[yesterday, stocks]
                )
                
             index_value_today = (units * self.prices.loc[today, stocks]).sum()
             
             index_return = (index_value_today / current_index_value) - 1 
             self.index_returns[today] = index_return
             
             current_index_value = index_value_today
            
        self.index_returns = pd.Series(self.index_returns)


        """
        self.index_values is a Series containing the index levels, starting from the base level 100.
        """

    

        self.index_values = (1 + self.index_returns).cumprod() * self.base_level
        self.index_values.loc[pd.Timestamp(start_date)] = self.base_level
        self.index_values = self.index_values.sort_index()

        
    
    def export_values(self, file_name: str) -> None:
        self.index_values.round(2).to_csv(file_name, header=["index level"], index_label=["Date"], mode="w")
