import os
import pyotp
import pandas as pd
from dotenv import load_dotenv
from helium import start_chrome
from utils import (login, create_new_app, create_app_page2, create_app_page3, create_app_page4, create_app_page5,
                   random_sleep)
import google.generativeai as genai


load_dotenv()
if __name__ == "__main__":
    email = os.environ["EMAIL"]
    password = os.environ["PASSWORD"]
    totp = pyotp.TOTP(os.environ["TOTP"])

    config_df = pd.read_excel("config.xlsx", sheet_name="config", index_col=0)

    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-pro')
    import pdb
    driver = start_chrome()
    login(driver, email, password, totp)
    for row in config_df.itertuples():
        create_new_app(driver, row.app_name, row.app_category, row.app_sub_category)
        random_sleep(min_=4, max_=8)
        create_app_page2(driver, row.static_folder_path, row.game_features, row.language_support)
        random_sleep(min_=4, max_=8)
        create_app_page3(driver)
        random_sleep(min_=4, max_=8)
        create_app_page4(driver, model, row.app_name, row.app_category, row.app_sub_category, row.static_folder_path)
        random_sleep(min_=4, max_=8)
        create_app_page5(driver)
        input("execution complete press any key")