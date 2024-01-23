import os
import pyotp
import pandas as pd
from dotenv import load_dotenv
from helium import start_chrome
from utils import (login, create_new_app, create_app_page2, create_app_page3, create_app_page4, create_app_page5,
                   random_sleep)
from logger import logger
import google.generativeai as genai
import warnings

warnings.simplefilter(action='ignore', category=UserWarning)


load_dotenv()
if __name__ == "__main__":
    email = os.environ["EMAIL"]
    password = os.environ["PASSWORD"]
    totp = pyotp.TOTP(os.environ["TOTP"])

    logger.info("Reading the config file..")
    config_df = pd.read_excel("config.xlsx", sheet_name="config", index_col=0)
    logger.info(f"Found {config_df.shape[0]} apps in config file.")

    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-pro')

    driver = start_chrome()
    logger.info("Started chrome driver, logging into amazon portal")
    login(driver, email, password, totp)
    logger.info("Login success..")
    for row in config_df.itertuples():
        try:
            logger.info(f"Creating {row.app_name} app to portal..")
            create_new_app(driver, row.app_name, row.app_category, row.app_sub_category)
            logger.info(f"Processing step 2")
            random_sleep(min_=4, max_=8)
            create_app_page2(driver, row.static_folder_path, row.game_features, row.language_support)
            logger.info(f"Processing step 3")
            random_sleep(min_=4, max_=8)
            create_app_page3(driver)
            logger.info(f"Processing step 4")
            random_sleep(min_=4, max_=8)
            create_app_page4(driver, model, row.app_name, row.app_category, row.app_sub_category, row.static_folder_path)
            logger.info(f"Processing step 5")
            random_sleep(min_=4, max_=8)
            create_app_page5(driver)
            logger.info(f"Successfully created {row.app_name} app..")
        except Exception as e:
            logger.exception(e)
