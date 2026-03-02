from flask import Flask, render_template
import pandas as pd
from csv_preprocessing import Preprocessing

app = Flask(__name__)

folder_path = input("Enter the path of the folder: ") # Taking folder path input
preprocess = Preprocessing(folder_path) #Initializing the Preprocessing file


csv_files = preprocess.get_csv_files() # Collecting CSV files
print("CSV Files Found:", csv_files)

for files in csv_files:
    stats = preprocess.statistics_of_dataset(files)
    print(f"-------------------Statistics of the file: {files}-------------------\n")
    print("-------------------Shape of the dataset-------------------\n", stats.shape)
    print("-------------------Quick info of the dataset-------------------\n", stats.info())
    print("-------------------Statistical summary of the dataset-------------------\n", stats.describe())
    print("-------------------Missing/null values in the dataset-------------------\n", stats.isna().sum())
    print("-------------------Duplicates in the dataset-------------------\n", stats.duplicated().sum())
    # print("------------------Correlation in the dataset-------------------\n", stats.corr())
    print("-------------------Random sample of the dataset-------------------\n", stats.sample(5))





# @app.route("/")
# def show_table():
#     # Load CSV file
#     df = pd.read_csv("Target_Retail_Customer_Retention_Analytics/Customer_Demographics.csv")   # replace with your CSV file path

#     # Convert DataFrame to HTML table
#     table_html = df.to_html(classes="table table-striped", index=False)

#     return render_template("table.html", table=table_html)

# if __name__ == "__main__":
#     app.run(debug=True)
