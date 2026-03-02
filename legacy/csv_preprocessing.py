import pandas as pd
import os

class Preprocessing:

    def __init__(self, folder_path):
        self.folder_path = folder_path
        self.csv_list = []

    def get_csv_files(self): #Loading csv files
        for file in os.listdir(self.folder_path):
            if file.endswith(".csv"):
                full_path = os.path.join(self.folder_path, file)
                self.csv_list.append(full_path)

        return self.csv_list

    def statistics_of_dataset(self, files):
        df = pd.read_csv(files)
        # shape = df.shape
        # info = df.info()
        # describe = df.describe()
        return df



        








#------------------------------------Iterating each dataset for statistics/information-------------------------------------

