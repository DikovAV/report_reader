import pandas as pd
import numpy as np



class report_reader():

    '''
    # ReportReader

    Class to read different brokers' reports
    '''

    @classmethod
    def reader(cls, link:str):
        '''
        ## reader:
        ---
        Method to read broker report. Now reports allowed:
        1. VTB - search and clean all unnecessary data.
        2. Binance - format data

        ## Parameters:
        ---
        link:str 
            Path to data.

        ## Return:
        ---
        pd.DataFrame
            A DataFrame with trades. Include ticker, price, quantity, and fee
        '''
        name = link.split('/')
        name = name[-1].split('.')
        broker_type = report_reader.__define_broker(name[0])
        try:
            if broker_type == 'vtb':
                df = report_reader.__processing_data_vtb(link)
                return df
            elif broker_type == 'binance':
                df = report_reader.__processing_data_binance(link)
                return df
        except:
            print('Не подходящий формат данных')

    @staticmethod
    def __define_broker(name):
        if name.lower().split()[0] == 'export':
            return 'binance'
        else:
            return 'vtb'
        
    @staticmethod
    def __processing_data_vtb(link:str):
        df = pd.read_excel(io=link)
        df.dropna(axis=0, how='all', inplace=True)
        df.dropna(axis=1, how='all', inplace=True)
        df.reset_index(drop=True,inplace=True)
        header_text = "Сделки с Производными финансовыми инструментами в отчетном периоде"
        header_row = df[df['Unnamed: 1'].str.contains(header_text, case=False, na=False)]
        start_data = header_row.index[0] + 1
        end_data = header_row.index[1]
        df = df.iloc[start_data:end_data]
        df.dropna(axis=1, how='all', inplace=True)
        df = df.iloc[1:,0:8]
        df.columns = ['ticker','datetime','side','q','price','drop','fee_1','fee_2']
        df['q'] = np.where(df['side'] == 'Продажа', -df['q'], df['q'])
        df.set_index(pd.to_datetime(df['datetime']),inplace=True)
        df.drop(columns=['drop','side','datetime'],inplace=True)
        df[['price','fee_1','fee_2']] = df[['price','fee_1','fee_2']].astype('float64')
        df['fee'] = df['fee_1'] + df['fee_2']
        df.drop(columns=['fee_1','fee_2'], inplace=True)
        df['q'] = df['q'].astype('int')
        return df[['ticker','price','q','fee']]
    
    @staticmethod
    def __processing_data_binance(link:str):
        df = pd.read_excel(io=link,
                            parse_dates={'datetime':['Date(UTC)']},
                            index_col='datetime')
        df['Filled'] = np.where(df['Type'] == 'SELL',
                                      df['Filled'] * -1,
                                      df['Filled'])
        df.drop(columns=['OrderNo','Type','AvgTrading Price','Order Amount','Total','Trigger Condition','status'],
                inplace=True)
        df.columns = ['ticker','price','q']
        df['fee'] = 0
        return df[['ticker','price','q','fee']]