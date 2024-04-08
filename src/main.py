import os
import shutil

import pandas as pd
from dotenv import load_dotenv
from helium import start_chrome, kill_browser

from apk_downloader_v2 import download_apk_data
from utils import (login, create_new_app, create_app_page2, create_app_page3, create_app_page4, create_app_page5,
                   random_sleep, STATIC_DATA, modify_apk)
from logger import logger
import google.generativeai as genai
import warnings

warnings.simplefilter(action='ignore', category=UserWarning)
warnings.simplefilter(action='ignore', category=DeprecationWarning)


load_dotenv()
if __name__ == "__main__":

    logger.info("Reading the config file..")
    config_df = pd.read_excel("config.xlsx", sheet_name="config", index_col=0)
    creds_df = pd.read_excel("config.xlsx", sheet_name="creds", index_col=0)
    logger.info(f"Found {config_df.shape[0]} total apps in config file.")

    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-pro')

    unique_usernames = config_df.username.unique()

    for username in unique_usernames:
        logger.info(f"Using username {username} credentials to create apps..")
        creds_dict = creds_df.query(f"username == '{username}'").to_dict("records")[0]
        user_df = config_df.query(f"username == '{username}'")
        logger.info(f"Found {user_df.shape[0]} apps for user {username}")
        temp_df_chunks = [user_df.iloc[i:i+5, :] for i in range(0, user_df.shape[0], 5)]

        apk_data = {}
        for row in user_df.itertuples():
            try:
                package_dir, app_name = download_apk_data(row.google_play_apk_url)
                apk_filepath = modify_apk(row.base_apkname, row.package_name)
                shutil.copy(apk_filepath, package_dir)
                apk_data[row.Index] = {"app_name": app_name, "package_dir": package_dir}
            except Exception as e:
                logger.error(f"Error while downloading and modifying apk {row.google_play_apk_url}, {e}")

        for temp_df in temp_df_chunks:
            driver = start_chrome()
            driver.maximize_window()
            logger.info("Started chrome driver, logging into amazon portal")
            login(driver=driver, email=creds_dict["email"], password=creds_dict["password"],
                  totp=creds_dict["TOTP"])
            logger.info("Login success..")
            for row in temp_df.itertuples():
                try:

                    if not apk_data.get(row.Index):
                        logger.info(f"Skipping {row.google_play_apk_url}, error while downloading apk.")
                        continue

                    package_dir, app_name = apk_data[row.Index]["package_dir"], apk_data[row.Index]["app_name"]
                    logger.info(f"package_dir: {package_dir}, app_name: {app_name}")
                    logger.info(f"Creating {app_name} app to portal..")
                    create_new_app(driver, app_name, row.app_category, row.app_sub_category)
                    logger.info(f"Processing step 2")
                    random_sleep(min_=4, max_=8)
                    create_app_page2(driver, package_dir, row.game_features, row.language_support)
                    logger.info(f"Processing step 3")
                    random_sleep(min_=4, max_=8)
                    create_app_page3(driver)
                    logger.info(f"Processing step 4")
                    random_sleep(min_=4, max_=8)
                    create_app_page4(driver, model, app_name, row.app_category, row.app_sub_category, package_dir)
                    logger.info(f"Processing step 5")
                    random_sleep(min_=4, max_=8)
                    create_app_page5(driver)
                    logger.info(f"Successfully created {app_name} app..")
                except Exception as e:
                    logger.exception(e)
            driver.get(STATIC_DATA["logout_url"])
            logger.info(f"Logged out user {username} successfully..")
            random_sleep(min_=4, max_=8)
            kill_browser()
        logger.info(f"All App submission for user {username} is complete..")
    logger.info("Done submitting all apps, closing browser..")
