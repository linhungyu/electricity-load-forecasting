import warnings
import numpy as np, pandas as pd
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
import matplotlib.pyplot as plt

import statsmodels.api as sm






def load_old_data(file_name):
    
    data_orig = pd.read_csv(file_name)
    df = data_orig[["日期", "備轉容量(MW)"]]
    df = change_col_name(df, "日期", "Date")
    df = change_col_name(df, "備轉容量(MW)", "OR")
    
    df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m-%d')  # convert date column to DateTime
    # print( df['Date'][2]) 
    df.set_index('Date', inplace=True)

    
    return df





def change_col_name(data, old_name, new_name):
    return data.rename(columns={old_name: new_name})



class SARIMA():
    def __init__(self):
        pass

    def load_data(self, file_name):
        
        data_orig = pd.read_csv(file_name)
        df = data_orig[["日期", "備轉容量(MW)"]]
        df = change_col_name(df, "日期", "Date")
        df = change_col_name(df, "備轉容量(MW)", "OR")
        
        df['Date'] = pd.to_datetime(df['Date'], format='%Y%m%d')  # convert date column to DateTime
        # print( df['Date'][2]) 
        df.set_index('Date', inplace=True)
        
        return df


    def TestStationaryPlot(self, df):
        rol_mean = df.rolling(window = 1, center = False).mean()
        rol_std = df.rolling(window = 1, center = False).std()
        
        #plt.plot(figsize=(15, 8))
        plt.plot(df, color = 'blue',label = 'Original')
        plt.plot(rol_mean, color = 'red', linestyle='-.', label = 'Moving Average')
        plt.plot(rol_std, color ='black', linestyle='--', label = 'Standard Deviation')
        plt.xticks(fontsize = 16)
        plt.yticks(fontsize = 16)

        plt.xlabel('Time', fontsize = 16)
        plt.ylabel('CO2', fontsize = 16)
        plt.legend(loc='best', fontsize = 16)
        plt.title('Moving Average and Standard Deviation', fontsize = 22)
        plt.show(block= True)

    def TestStationaryAdfuller(self, df, cutoff = 0.2):
        from statsmodels.tsa.stattools import adfuller
        df_test = adfuller(df, autolag = 'AIC')
        df_test_output = pd.Series(df_test[0:4], index=['Test Statistic','p-value','#Lags Used','Number of Observations Used'])

        for key,value in df_test[4].items():
            df_test_output['Critical Value (%s)'%key] = value
        print(df_test_output)

        if df_test[1] <= cutoff:
            print('拒绝原假设，即数据没有单位根,序列是平稳的。')
        else:
            print('不能拒绝原假设，即数据存在单位根,数据是非平稳序列。')
            
            
    def deviate(self, df):
        from statsmodels.graphics.tsaplots import acf,pacf,plot_acf,plot_pacf
        from statsmodels.graphics.api import qqplot 
        y_diff = df.diff(1)
        y_seasonal_diff = y_diff - y_diff.shift(12)
        
        return y_seasonal_diff


    def method2(self, y):
        '''
        Use grid method to find out the best q, d, p
        '''
        import itertools
        # 首先定义 p、d、q 的参数值范围，这里取 0 - 2.
        p = d = q = range(0, 3)

        # 然后用itertools生成不同的参数组合
        pdq = list(itertools.product(p, d, q))
        
        # 同理处理季节周期性参数，也生成相应的多个组合
        seasonal_pdq = [(x[0], x[1], x[2], 12) for x in list(itertools.product(p, d, q))]

        print('Examples of parameter combinations for Seasonal ARIMA...')
        print('SARIMAX: {} x {}'.format(pdq[1], seasonal_pdq[1]))
        print('SARIMAX: {} x {}'.format(pdq[1], seasonal_pdq[2]))
        print('SARIMAX: {} x {}'.format(pdq[2], seasonal_pdq[3]))
        print('SARIMAX: {} x {}'.format(pdq[2], seasonal_pdq[4]))

        warnings.filterwarnings('ignore') 
        for param in pdq:
            for param_seasonal in seasonal_pdq:
                try:
                    mod = sm.tsa.statespace.SARIMAX(y, order=param, seasonal_order=param_seasonal, enforce_stationarity=False,
                                                    enforce_invertibility=False)
                    results = mod.fit()
                    print('SARIMAX{}x{}12 - AIC:{}'.format(param, param_seasonal, results.aic))
                except:
                    continue


    def white_noise(self, y_seasonal_diff):
        #再对1阶12步差分后序列做白噪声检验
        warnings.filterwarnings('ignore') 
        y_seasonal_diff.dropna(inplace = True)
        r,q,p = sm.tsa.acf(y_seasonal_diff.values.squeeze(), qstat=True) 
        data = np.c_[range(1,41), r[1:], q, p] 
        
        table = pd.DataFrame(data, columns=['lag', 'AC', 'Q', 'Prob(>Q)']) 
        print(table.set_index('lag')) 
        
        return


    def train(self, y):
        mod = sm.tsa.statespace.SARIMAX(y,
                                    order=(1, 1, 1),
                                    seasonal_order=(1, 1, 1, 12),
                                    enforce_stationarity=False,
                                    enforce_invertibility=False)

        results = mod.fit()
        print(results.summary().tables[1])
        # results.plot_diagnostics(figsize=(12, 10))
        return results


    def validate(self, results, date_start):
        pred = results.get_prediction(start=date_start, dynamic=False)
        pred_ci = pred.conf_int()
        return pred, pred_ci
        

    def calculate_rmse_error(self, y, pred, start_time):
        y_forecasted = pred.predicted_mean
        y_truth = y[start_time:]
        y_truth = y_truth.squeeze()
        
        mse = ((y_forecasted - y_truth) ** 2).mean()
        # print('The Mean Squared Error of forecasts is {}'.format(round(mse, 2)))
        print('The Root Mean Squared Error of forecasts is {}'.format(np.sqrt(sum((y_forecasted-y_truth)**2)/len(y_forecasted))))
        return


    def predict(self, results, date_start):
        pred = results.forecast(steps=15, dynamic=True)
        print(pred)
        # mask = (df['日期'] >= '2022-03-30') & (df['日期'] <= '2022-04-13')
        print(pred[1])
        return pred


    def make_figure(self, df):
        ax = df.plot(label='Original')
        
        pred.predicted_mean.plot(ax=ax, label='One-step ahead Forecast', alpha=.7)

        ax.fill_between(pred_ci.index,
                        pred_ci.iloc[:, 0],
                        pred_ci.iloc[:, 1], color='k', alpha=.2)

        ax.set_xlabel('Date')
        ax.set_ylabel('OR')
        plt.legend()
        plt.show()
        return


    def main(self, training_data):

        # df1 = load_old_data('test.csv')
        df = self.load_data(training_data)
        # df = pd.concat([df1, df2], axis=0)

        self.TestStationaryAdfuller(df)      
        y_seasonal_diff = self.deviate(df)
        self.TestStationaryAdfuller(y_seasonal_diff.dropna(inplace=False))
        
        # ========= Use grid method to find out the best q, d, p =========
        # method2(df)
        
        # ================== start training ==================
        results = self.train(df)
        
        # ================== validate ==================
        # start_time = "2022-01-01"
        # pred, pred_ci = validate(results, start_time)
        # calculate_rmse_error(df, pred, start_time)

        # ================== make prediction ==================
        
        prediction_result  = self.predict(results, '2022-03-30')
        # exit()
        # print(pred.predicted_mean)
        
        # ================== Make figures ==================
        # make_figure(df)
        
        return prediction_result






if __name__ == "__main__":
    arima_main("raw_data.csv")