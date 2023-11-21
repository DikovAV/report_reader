from .report_reader import report_reader
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

class broker_report():

    '''
    Describe
    -----------------

    Class containing information about trades. There are three levels of information: Initial information, summary information per trade, and overall summary.

    Parameters
    ----------------
    link:str
        Path to the broker report
    initial_cast : [int, float]
        Initial money to calculate DD and Cumulative PnL

    Methods
    -----------------
    statistic_calc:
        Calculate extra information about trades like entry price, average price, pnl, and cumulative pnl.

    summary_calc:
        Calculate overall summary information about all trades.

    summary_per_trade:
        Calculate summary information per ticker.
    '''


    dict_of_price_step_value = {
            'si' : 1,
            'br' : 700,
            'go' : 70,
            'ed' : 600, 
    }

    def __init__(self,
                 link='/path_to_report.xls',
                 init_cash=100000) -> None:
        self.df = report_reader.reader(link)
        self.statistic_calc(init_cash)
        self.summary_calc()
        self.summary_per_trade_calc()


    def statistic_calc(self,init_cash:float):
        '''
        statistic_calc
        -------------
        Method for calculating extra information about trades like entry price, average price, pnl, and cumulative pnl.

        Parameters:
        -------------
        init_cash: int
            Default value = 100000

        Return:
        -------------
        self.df : pd.DataFrame
            A DataFrame with general information about trades. Trade number, operation (long/short), average entry price, pnl, cumulative pnl
        '''

        self.df['position'] = self.df.groupby('ticker')['q'].cumsum()

        self.df['num_of_trade_by_ticker'] = np.where(self.df['position'] == 0,
                                                     1,
                                                     0)
        self.df['trade_num'] = np.where(self.df['position'] == 0,
                                                     self.df.groupby('num_of_trade_by_ticker').cumcount(),
                                                     np.nan)
        self.df['trade_num'] = self.df.groupby('ticker')['trade_num'].fillna(method='bfill')
        self.df.drop(columns=['num_of_trade_by_ticker'], inplace=True)
        self.df['avg_entry_price'] = self.df['price'] * self.df['q']
        self.df['avg_entry_price'] = self.df.groupby('trade_num')['avg_entry_price'].cumsum() / self.df.groupby('trade_num')['q'].cumsum()
        self.df.loc[self.df['position'] == 0, 'avg_entry_price'] = self.df.loc[self.df['position'] == 0, 'avg_entry_price'].shift(1)
        self.df['avg_entry_price'] = np.where(self.df['position'] == 0,
                                              np.nan,
                                              self.df['avg_entry_price'])
        self.df['avg_entry_price'] = self.df.groupby('trade_num')['avg_entry_price'].transform(lambda x: x.ffill())
        self.df['trade_side'] = np.where(self.df.groupby('trade_num')['position'].transform('first') >= 0, 'long', 'short')
        self.df['pnl'] = np.where(
              self.df['position'] == 0,
              (self.df['price'] - self.df['avg_entry_price']) * -np.sign(self.df['q']) * abs(self.df['q'])
              * self.df['ticker'].str.lower().str[:2].map(broker_report.dict_of_price_step_value), 
             np.nan)
        self.df['cum_pnl'] = self.df['pnl'].cumsum() + init_cash

    

    def summary_calc(self):

        '''
        summary_calc
        -------------
        Method for calculating summary information about trades

        Return:
        -------------
        self.summary : pd.DataFrame
            A DataFrame with summary information like the number of trades, average profit and loss, win rate, profit factor, average trade result, max drawdown
        '''

        self.summary = pd.DataFrame()
        self.summary.loc['summary','pnl'] = self.df['pnl'].sum()
        self.summary['count'] = self.df['pnl'].count()
        self.summary['profit'] = self.df.loc[self.df.pnl > 0,'pnl'].mean()
        self.summary['lose'] = self.df.loc[self.df.pnl <= 0,'pnl'].mean()
        self.summary['win_rate'] = abs(self.df.loc[self.df.pnl > 0,'pnl'].count() / 
                                           (self.df.loc[self.df.pnl.notna(),'pnl'].count()))
        self.summary['profit_factor'] = abs(self.summary['profit'] / self.summary['lose'])
        self.summary['expected_value'] = 1 + self.summary['win_rate'] * self.summary['profit_factor']
        self.summary['max_dd'] = ((self.df['cum_pnl'].cummax() - self.df['cum_pnl']) / self.df['cum_pnl'].cummax() * 100).max()
        self.summary = self.summary.sort_values(by='pnl', ascending=False)
    
    def summary_per_trade_calc(self):
        '''
        summary_per_trade_calc
        ----------------------
        Compute per-ticker summary metrics.

        Returns:
        -------------
        self.summary_per_trade : pd.DataFrame
            DataFrame presenting summary metrics per ticker, encompassing total pnl, trade count, average profit, average loss, win rate, profit factor, and expected average value.
        '''
        unique_ticker = self.df.ticker.unique()
        self.summary_per_trade = pd.DataFrame()
        for ticker in unique_ticker:
            cond = self.df['ticker'] == ticker
            self.summary_per_trade.loc[ticker, 'pnl'] = self.df.loc[cond,'pnl'].sum()
            self.summary_per_trade.loc[ticker,'count'] = self.df.loc[cond,'pnl'].count()
            self.summary_per_trade.loc[ticker, 'profit'] = self.df.loc[(cond) & (self.df.pnl > 0),'pnl'].mean()
            self.summary_per_trade.loc[ticker, 'lose'] = self.df.loc[(cond) & (self.df.pnl <= 0),'pnl'].mean()
            self.summary_per_trade.loc[ticker, 'win_rate'] = abs(self.df.loc[(cond) & (self.df.pnl > 0),'pnl'].count() / 
                                           (self.df.loc[(cond) & (self.df.pnl.notna()),'pnl'].count()))
            self.summary_per_trade.loc[ticker, 'profit_factor'] = abs(self.summary_per_trade.loc[ticker, 'profit'] /
                                                self.summary_per_trade.loc[ticker, 'lose'])
            self.summary_per_trade.loc[ticker, 'expected_avg_value'] = ((1 - self.summary_per_trade.loc[ticker, 'win_rate']) * self.summary_per_trade.loc[ticker, 'lose'] + 
                                                     (self.summary_per_trade.loc[ticker, 'win_rate']) * self.summary_per_trade.loc[ticker, 'profit'])
            self.summary_per_trade = self.summary_per_trade.sort_values(by='pnl', ascending=False)


    def plot_unique_tickers(self, amount=5):
        '''
        plot_unique_tickers
        --------------------
        Generate a bar plot displaying the top 5 tickers based on the number of trades.

        '''

        plt.figure(figsize=[8, 6])
        plt.title('Top-5 tickers', fontsize=15)
        data_val = self.df.loc[self.df.pnl.notna(), 'ticker'].value_counts().sort_values(ascending=False).head(amount)
        sns.barplot(y = data_val.values,
                    x = data_val.index,
                    hue = data_val.index,
                    alpha=0.7,)
        plt.xlabel('Ticker')
        plt.ylabel('Number of trades')


    def plot_cum_pnl(self):
        '''
        plot_cum_pnl
        -------------
        Generate a line plot illustrating the Profit and Loss (PnL) statement over time.
        '''
        plt.figure(figsize=[12, 8])
        plt.title('Profit and loss statement', fontsize=15)
        sns.lineplot(data=self.df.loc[self.df.cum_pnl.notna(),'cum_pnl'].reset_index(drop=True))
        plt.ylabel('Cumulative PnL')
        plt.xlabel('Time')
        plt.show()