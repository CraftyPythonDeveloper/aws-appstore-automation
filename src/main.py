import os
import shutil
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from helium import start_chrome, kill_browser

from apk_downloader_v2 import download_apk_data
from utils import (login, create_new_app, create_app_page2, create_app_page3, create_app_page4, create_app_page5,
                   random_sleep, STATIC_DATA, modify_apk, update_running_status)
from logger import logger
import google.generativeai as genai
import warnings

warnings.simplefilter(action='ignore', category=UserWarning)
warnings.simplefilter(action='ignore', category=DeprecationWarning)


load_dotenv()

SRC_DIR = Path(__file__).resolve().parents[1]
INPUT_APK_DIR = os.path.join(SRC_DIR, "src", "base_apk")
# TEMP_OUTPUT_DIR = os.path.join(INPUT_APK_DIR, "temp")


def run(use_local_apk, change_package_name, drm_status, start_from, *args, **kwargs):
    global driver
    logger.info("Reading the config file..")
    config_df = pd.read_excel("config.xlsx", sheet_name="config", index_col=0)
    creds_df = pd.read_excel("config.xlsx", sheet_name="creds", index_col=0)
    logger.info(f"Found {config_df.shape[0]} total apps in config file.")

    if start_from:
        start_from = int(start_from) if start_from == 0 else int(start_from)-1
        logger.info(f"Starting from {start_from}")
        config_df = config_df[start_from:]

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
                if use_local_apk:
                    package_dir, app_name = download_apk_data(row.google_play_apk_url, download_apk=False)
                    apk_name = row.base_apkname
                    shutil.copy(os.path.join(INPUT_APK_DIR, apk_name), package_dir)
                else:
                    package_dir, app_name = download_apk_data(row.google_play_apk_url)
                    apk_name = f"{''.join(e for e in app_name if e.isalnum())}.apk"

                org_apk_filepath = os.path.join(package_dir, apk_name)

                if not os.path.isfile(org_apk_filepath):
                    logger.debug(f"APK file not found for {app_name}, path is {org_apk_filepath}")
                    continue

                if not package_dir:
                    raise AttributeError("Unable to download apk file.")

                try:
                    # if change package name is checked or use local apk is checked.
                    if change_package_name:
                        apk_filepath = modify_apk(apk_name, row.package_name, package_dir)
                        if not apk_filepath:
                            logger.info("Unable to modify the apk.")
                            continue

                        if org_apk_filepath:
                            os.remove(org_apk_filepath)

                    # when download apk is checked and no modification is checked, then we just download and continue.
                    apk_data[row.Index] = {"app_name": app_name, "package_dir": package_dir}
                except Exception as e:
                    logger.error("Error while modifying apk {exc}".format(exc=str(e)))
                    shutil.rmtree(package_dir)
            except Exception as e:
                logger.error(f"Error while downloading and modifying apk {row.google_play_apk_url}, {e}")

        for temp_df in temp_df_chunks:
            driver = start_chrome()
            driver.maximize_window()
            logger.info("Started chrome driver, logging into amazon portal")
            login_status = login(driver=driver, email=creds_dict["email"], password=creds_dict["password"],
                                 totp=creds_dict["TOTP"])
            if not login_status:
                logger.info(f"Login Failed for user {creds_dict['email']}")
                driver.close()
                break
            logger.info("Login success..")
            for row in temp_df.itertuples():
                if not apk_data.get(row.Index):
                    logger.info(f"Skipping {row.google_play_apk_url}, error while downloading apk.")
                    continue

                package_dir, app_name = apk_data[row.Index]["package_dir"], apk_data[row.Index]["app_name"]
                try:
                    logger.info(f"package_dir: {package_dir}, app_name: {app_name}")
                    logger.info(f"Creating {app_name} app to portal..")
                    create_new_app(driver, app_name, row.app_category, row.app_sub_category)
                    logger.info(f"Processing step 2")
                    random_sleep(min_=4, max_=8)
                    create_app_page2(driver, package_dir, row.game_features, row.language_support, drm=drm_status)
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

                try:
                    # cleanup the dir
                    shutil.rmtree(package_dir)
                    logger.info(f"Done cleaning up {package_dir} dir")
                except Exception as e:
                    logger.error(f"Error occurred while removing the apk dir {package_dir}, Error: {e}")

            driver.get(STATIC_DATA["logout_url"])
            logger.info(f"Logged out user {username} successfully..")
            random_sleep(min_=4, max_=8)
            kill_browser()
        logger.info(f"All App submission for user {username} is complete..")
    logger.info("Done submitting all apps, closing browser..")
    update_running_status("stopped")
