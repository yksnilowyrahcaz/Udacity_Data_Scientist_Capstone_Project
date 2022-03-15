import sys
import time
import torch
import datetime
import calendar
import numpy as np
import pandas as pd
from collections import defaultdict
from sklearn.preprocessing import MinMaxScaler, LabelEncoder

class Preprocessor:
    '''
    Class to preprocess the City of Philadelphia payments dataset
    so that it can be passed through a neural network.
    '''
    def process(self, df):
        '''
        Cleans up the City of Philadelphia FY17 payments data
        by removing redundant columns, filling NaN values with 
        'None', and adding useful features including 'amount_sign',
        'payment_method', 'weekday','day', 'month', and 'year'

        Args:
            df: 
                pandas DataFrame, the result of calling
                pd.read_csv('data/city_payments_fy2017.csv')
        '''
        
        # remove redundant columns, fill NaN with 'None', add features
        print('Cleaning data...')
        df.department_title = df.department_title.str.split().apply(
            lambda x: ' '.join(x[1:len(x)]))

        df.character_title = df.character_title.str.split().apply(
            lambda x: ' '.join(x[1:len(x)]))

        df.sub_obj_title = df.sub_obj_title.str.split().apply(
            lambda x: ' '.join(x[0:len(x)-1]))

        df['amount_sign'] = df.transaction_amount.apply(
            lambda x: 1 if x >= 0 else 0)

        df.transaction_amount = df.transaction_amount.abs()

        df['payment_method'] = df.document_no.str.split('1').apply(
            lambda x: x[0])

        df['weekday'] = df.check_date.str.split('-').apply(
            lambda x: calendar.day_name[
            datetime.datetime(int(x[0]), 
                              int(x[1]), 
                              int(x[2])).weekday()])

        df['day'] = df.check_date.str.split('-').apply(
            lambda x: x[2])

        df['month'] = df.check_date.str.split('-').apply(
            lambda x: calendar.month_name[int(x[1])])

        df['year'] = df.check_date.str.split('-').apply(
            lambda x: x[0])

        df.drop(['fy', 'fm', 'check_date', 'dept', 'char_', 'sub_obj', 
                 'doc_ref_no_prefix','contract_number'], 
                axis=1, inplace=True)

        df.fillna('None', inplace=True)
        
        self.preprocessed = df

        # determine categorical and numerical features
        self.numerical = df.select_dtypes(include=['int64', 'float64']).columns
        self.categorical = df.select_dtypes(include=['object', 'bool']).columns
        
        # Get feature names for plotting
        self.feature_names = dict(zip(range(len(self.categorical) +\
                                            len(self.numerical)-1),
                                      self.categorical.tolist()[1:] +\
                                      self.numerical.tolist()))

        # label encode categorical features
        print('Label encoding the data...')
        self.le = defaultdict(LabelEncoder)
        self.Y = df[self.categorical].apply(
            lambda x: self.le[x.name].fit_transform(x))
        self.Y = pd.concat([self.Y, df[self.numerical]], axis=1)

        # Take a sample that will become our X matrix
        print('Sampling from the original data...')
        self.df_sample = df.sample(n=128*373, random_state=1729).drop(
            columns='document_no')

        # Take another sample using the same random_sate
        # thus, same indices as df_sample, to use to recover labels
        self.Y_sample = self.Y.sample(n=128*373, random_state=1729)

        # create dummy variables to one-hot-encode
        print('One-hot-encoding the data...')
        self.X = pd.get_dummies(self.df_sample, drop_first=True)

        # min-max scale the transaction amount
        self.X.transaction_amount = MinMaxScaler().fit_transform(
            self.X.transaction_amount.to_numpy().reshape(-1,1))

        # create tensors
        print('Generating tensors...')
        self.X_ = torch.FloatTensor(self.X.values)
        self.Y_ = torch.FloatTensor(self.Y_sample.values)
        
        # combine X_ and Y_ into a single dataset
        print('Combining tensors into one dataset...')
        self.dataset = torch.utils.data.TensorDataset(self.X_, self.Y_)
        self.dataset = torch.utils.data.DataLoader(self.dataset, 
                                                   batch_size=128, 
                                                   shuffle=True)

    def recover_labels(self, Y):
        '''
        Recover data labels from tensor to pandas DataFrame
        by applying the inverse transform of the label encoder
        on the label encoded payments data
        
        Parameters:
            Y: torch.Tensor of the label encoded payments data
            
        Returns:
            recovered_Y: pandas DataFrame of payments data
            with interpretable labels instead of encoded numbers
        '''
        recovered_Y = pd.concat([
            pd.DataFrame(Y, columns=self.Y_sample.columns)[self.categorical]\
            .astype('int32').apply(lambda x: self.le[x.name].inverse_transform(x)), 
            pd.DataFrame(Y, columns=self.Y_sample.columns)[self.numerical]
        ], axis=1)

        return recovered_Y
    
def main():
    if len(sys.argv) == 2:
        start_time = time.time()
        philly_payments_filepath = sys.argv[1]
        print(f'Loading data from: {philly_payments_filepath}')
        df = pd.read_csv(philly_payments_filepath)
        pre = Preprocessor()
        pre.process(df)
        torch.save(pre, 'data/philly_payments_clean')
        print('Preprocessing complete!')
        print(f'Total Time: {round((time.time() - start_time)/60, 2)} minutes')
    
    else:
        print(
            '''
        Please provide the filepath of the philly payments data.
            
        Example: python data/preprocessing.py data/city_payments_fy2017.csv
            '''
        )
            
if __name__ == '__main__':
    main()