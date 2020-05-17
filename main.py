# Fixing and Interest Rates provider

"""
The following script gathers fixing and interest rates quotes by making API calls (FX Rates) and scraping the EMMI webpage (Interest Rates)

Fixing: Daily fixing rates such as EUR/USD, EUR/NOK, etc.

Interest rates gathered:
- EURIBOR: 1 week, 1 month, 3 months, 6 months, 12 months.
- EONIA: ON.
"""

# Imports
import pandas as pd
import matplotlib.pyplot as plt
import requests
import csv
import os
import time


# Constants
API_KEY = "123456789" # Alpha Vantage personal key
API_URL = "https://www.alphavantage.co/query?"

# Main variables
local = "data/Historical_Rates.csv"
saveto = f"data/Rates_to_upload_{int(time.time())}.csv"

# Data to look up in the webpage and API
rates_to_look_up = ["EURIBOR", "USD", "NOK", "GBP", "JPY", "CHF", "EONIA"]
years = ["2020", "2019"]

# Filter parameters
filter_list = ["USD", "GBP", "NOK", "EURIBOR", "EONIA"]
from_date = "01/01/2020"
to_date = "15/05/2020"


def format_date(date_str):
    """
    Takes a date like string such as 2020-05-11 and returns 11/05/2020.
    :param date_str: date like string to convert.
    """
    date_list = date_str.split("-")
    nice_date = "/".join(date_list[::-1])
    return nice_date


# Getting fixing from Alpha Vantage API
def get_single_fixing(from_cur, to_cur, api_url=API_URL, key=API_KEY):
    """
    Returns a df with the last 100 quotes of a given pair (from_cur: base currency, to_cur: quote currency).
    :param from_cur: Base currency.
    :param to_cur: Quote currency.
    :param api_url: API URL.
    :param key: API key.
    """
    
    params = {"function": "FX_DAILY", "from_symbol": from_cur.upper(), "to_symbol": to_cur.upper(),
              "apikey": key, "datatype": "json"}
    r = requests.get(api_url, params=params)
    
    # Creates a df if the connection was successful
    if r.status_code == 200:
        r_json = r.json() # turns the response object into a JSON dictionary-like object

        too_quick = "standard API call frequency is 5 calls per minute and 500 calls per day"

        try:
            fix_df = pd.DataFrame(r_json["Time Series FX (Daily)"]).T # Creates a df
            fix_df.drop(columns=fix_df.columns[0:3], inplace=True) # Drops Open, High and Low columns
            fix_df.reset_index(inplace=True, drop=False) # Sets index as integers and places dates into a column
            fix_df["Currency"] = to_cur # Creates a new column with the quote currency (to_cur)
            fix_df.columns = ["Date", "Value", "Rate"] # Renames all columns
            fix_df["Date"] = fix_df["Date"].apply(lambda x : format_date(x)) # 2020-05-11 -> 11/05/2020
        
              # Use this to make a nice plot :)
#             fix_df.reset_index(drop=False, inplace=True)
#             fix_df.columns = ["Date", "Open", "High", "Low", "Close"] # Renames all columns
#             fix_df["Date"] = fix_df["Date"].apply(lambda x : format_date(x)) # 2020-05-11 -> 11/05/2020
#             fix_df["Currency Pair"] = f"{from_cur}/{to_cur}"

            return fix_df

        except LookupError:
            print("Alpha Vantage free account only supports 5 calls per minute and 500 calls per day")
            exit()
    
    else:
        print("Error retrieving fixing data from the API")
        return None


# Gathers Interest Rates from the EMMI webpage. It's a csv file.
def get_single_interest_rate(rate, year):
    """
    Returns a raw data frame with three columns; Rate, Value (close price), and Date.
    :param rate: Interest rate to request; EURIBOR or EONIA.
    :param year: Year to request being 1999 the oldest available year.
    """
    
    if rate.upper() == "EURIBOR":
    
        url = (f"https://www.emmi-benchmarks.eu/assets/components/rateisblue/"
               f"file_processing/publication/processed/hist_{rate.upper()}_{year}.csv")

        r = requests.get(url)

        if r.status_code == 200:
            # Formatting raw csv data into pandas dataframe
            raw_csv =  r.text.split("\n") # splits by /n
            raw_list = [row.lstrip(",").rstrip(",").split(",") for row in raw_csv] # splits the csv file into rows
            raw_list[0].insert(0, "Rate") # adds header, should be the same in the melt function below.
            raw_list.pop() # deletes last empty row
            raw_df = pd.DataFrame(raw_list[1:], columns=raw_list[0]) # creates df
            raw_df = pd.melt(raw_df, id_vars=["Rate"], value_vars=raw_df.columns[1:], 
                             var_name="Date", value_name="Value") # Turns columns (dates) into rows
            raw_df = raw_df[["Date", "Value", "Rate"]] # Rearranging columns

            return raw_df

        else:
            # if status code is different from 200, returns None
            print(f"Error downloading {rate} data from: {url}")
            return None
        
    elif rate.upper() == "EONIA":
        
        url = (f"https://www.emmi-benchmarks.eu/assets/components/rateisblue/"
               f"file_processing/publication/processed/hist_{rate.upper()}_{year}.csv")

        r = requests.get(url)

        if r.status_code == 200:
            # Formatting raw csv data into pandas dataframe
            raw_csv =  r.text.split("\n") # splits by /n
            raw_list = [row.lstrip(",").rstrip(",").split(",") for row in raw_csv] # splits the csv file into rows
            raw_list[0].insert(0, "Rate") # add missing header, should be the same that in the melt function below
            raw_list.pop() # deletes last empty row
            raw_list.pop() # deletes volume ON (in mln euro) row
            raw_df = pd.DataFrame(raw_list[1:], columns=raw_list[0]) # creates df
            raw_df = pd.melt(raw_df, id_vars=["Rate"], value_vars=raw_df.columns[1:], 
                             var_name="Date", value_name="Value") # Turns columns (dates) into rows
            raw_df = raw_df[["Date", "Value", "Rate"]] # Rearranging columns

            return raw_df

        else:
            # if status code is different from 200, returns None
            print(f"Error downloading {rate} data from: {url}")
            return None


def clean_df(original_df, clean_type):
    """
    Returns a 3 columns formatted dataframe.
    :param original_df: Raw 3 columns dataframe to enhance
    :param clean_type: "EURIBOR", "EONIA" or "FX"
    """
    df = original_df.copy()
    
    df["Value"] = pd.to_numeric(df["Value"])
    df["Rate"] = pd.Categorical(df["Rate"])
    
    # 1w -> EUR1W
    if  clean_type.upper() == "EURIBOR":
        df["Rate"] = df["Rate"].apply(lambda x: f"EUR{x.upper()}")
        
    
    elif clean_type.upper() == "EONIA":
        df["Rate"] = df["Rate"].apply(lambda x: f"EONIA")
    
    # Not specific formatting needed for fixing
    elif clean_type.upper() == "FX":
        pass

    return df


def create_local(local_file):
    """
    Creates a csv file to save historical rates. This file will be used to look up rates later on.
    :param local_file: Historical rates csv file path.
    """
    # Creates a csv file with just one row (headers) "Date", "Value" and "Rate"
    with open(local_file, "w") as f: 
        headers = [["Date", "Value", "Rate"]]
        csv_writer = csv.writer(f)
        for line in headers:
            csv_writer.writerow(line)
            return None


def update_local(local_file, df_to_add):
    """
    Updates rates file. This is where all looked up rates will be stored.
    :param local_file: Historical rates csv file path.
    :param df_to_add: Dataframe. New data to add to the csv.
    """
    # Checks whether the file exists. If not, it will create it. 
    if os.path.exists(local_file):
        df = pd.read_csv(local_file)
        
        # Check if it has the same format, it won't concatenate otherwise 
        comparison = df.columns == df_to_add.columns
        if comparison.all():
            full = pd.concat([df, df_to_add])
            full.drop_duplicates(subset=["Date", "Rate"], keep="first", inplace=True)
            full.to_csv(local_file, index=False)
            full.reset_index(drop=True, inplace=True)
            print(f"File updated: {local_file}")
            return full
        else:
            print(f"Dataframes cannot be concatenated."
                  f"local file columns: {len(df.columns)}, df to add columns: {len(df_to_add.columns)}")
            return None
        
    else:
        # Creates rates file and calls the same function again.
        create_local(local_file)
        print(f"New file created at: {local_file}")
        full_df = update_local(local_file, df_to_add)
        return full_df


def concatenator(list_of_df):
    """
    Takes a bunch of dataframes and blends them together vertically.
    :param list_of_df: List of dataframes.
    """
    full_df = pd.concat(list_of_df)
    sorted_df = full_df.sort_values(by=["Date", "Rate"])
    sorted_df.reset_index(inplace=True, drop=True)
    return sorted_df


def get_multiple_rates(list_rates, interest_rate_years):
    """
    Returns a dataframes with all requested rates
    :param list_rates: List of requested rates, FX and interest rates alike. ["EURIBOR", "USD", "NOK"]
    :param interest_rate_year: List of years, only applicable to interest rates. ["2020", "2019"]
    """
    print("Gathering data...")
    df_rates_list = [] # here will be stored all requested rates
    
    for rate in list_rates:
        # Runs interest rate function if rate is EURIBOR or EONIA
        if rate.upper() == "EURIBOR" or rate.upper() == "EONIA":
            # Loops through each requested year
            for year in interest_rate_years:
                print(f"Gathering {rate}, year {year}")
                current_interest_rate = clean_df(get_single_interest_rate(rate, year), rate)
                df_rates_list.append(current_interest_rate)
        
        # Runs fixing function if requested rate is different from EURIBOR or EONIA
        else:
            print(f"Gathering {rate}")
            current_fixing = clean_df(get_single_fixing("EUR", rate), "FX")
            df_rates_list.append(current_fixing)
    
    bunch_of_rates = concatenator(df_rates_list)
    print("Data gathered successfully!")
    
    return bunch_of_rates


def look_up(df_path, rates_list, date_from, date_to=0):
    """
    Filters historical data given a range of dates and a set of rates. Returns a df
    
    :param df_path: CSV file to sort through. 
    :param rates_list: Filter. Rates to show up (EUR12M, USD, GBP, etc)
    :param date_from: Initial date. Inclusive
    :param date_to: End date. Inclusive. This parameter will take date_from value if it's set to 0
    """
    
    # Switching day and month position
    date_from = date_from.split("/")
    date_from = date_from[1] + "/" + date_from[0] + "/" + date_from[2]
    
    # If date_to is empty, it will just return one day -> date_from
    if date_to == 0:
        date_to = date_from
    else:
        # Switching day and month position
        date_to = date_to.split("/")
        date_to = date_to[1] + "/" + date_to[0] + "/" + date_to[2]
        
    # Loading historical rates. csv file
    df = pd.read_csv(df_path)
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)
    
    # Turning all rates into uppercase and adding all possible Euribor rates
    rates_list = [i.upper() for i in rates_list]
    rates_list.extend(["EUR12M", "EUR9M", "EUR6M", "EUR3M", "EUR1M", "EUR1W"]) if "EURIBOR" in rates_list else None
    
    # Filtering and sorting data
    filtered_df = df.loc[(df.Date >= date_from) & (df.Date <= date_to) & (df.Rate.isin(rates_list))]
    sorted_df = filtered_df.sort_values(by=["Date", "Rate"], ascending=True, na_position="first")
    sorted_df.reset_index(drop=True, inplace=True)
    sorted_df.loc[:, "Date"] = sorted_df["Date"].dt.strftime("%d/%m/%Y")
    
    # Saving df into a csv file
    df.to_csv(saveto, index=False)
    print(f"Filtered data csv file saved at: {saveto}")
    
    return sorted_df


def main():
    # Getting rates from Alpha Vantage API and EMMI webpage
    df = get_multiple_rates(rates_to_look_up, years) # null values in 2018

    # Saving gathered rates into a csv file
    raw = update_local(local, df)

    # Filtering relevant rates and saving filtered data into a csv file (saveto)
    result = look_up(local, filter_list, from_date, to_date)
    print(result)


if __name__ == "__main__":
    main()

