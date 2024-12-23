import json
import os.path
import random
import shutil
import time
from pathlib import Path

from selenium.webdriver import ActionChains
from selenium.webdriver.support.wait import WebDriverWait
from seleniumbase import Driver
from logger import logger

from helium import *
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from amazoncaptcha import AmazonCaptcha
import pyotp
from apk_automations.apk import compile_apk, decompile_apk, change_package_name

SRC_DIR = Path(__file__).resolve().parents[1]
STATUS_FILEPATH = os.path.join(SRC_DIR, "src", "status.txt")
STATIC_DATA = {
    "dashboard_url": "https://developer.amazon.com/home.html",
    "create_new_app_url": "https://developer.amazon.com/apps-and-games/console/app/new.html",
    "scroll_top_query": "document.documentElement.scrollTop = 0;",
    "logout_url": "https://www.amazon.com/ap/signin?openid.return_to=https%3A%2F%2Fdeveloper.amazon.com%2Fapps-and"
                  "-games&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid"
                  ".assoc_handle=mas_dev_portal&openid.mode=logout&openid.claimed_id=http%3A%2F%2Fspecs.openid.net"
                  "%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0&language"
                  "=en_US",

}
prompt = """You are an android app description suggestion agent and your job is to generate short description, 
            long description and short feature description of android app by using below provided details and make sure
             to use response format as reference to provide response in the same key value pair, the response 
             format needs to be strictly followed, if required regenerate the response but make sure that the dictionary 
             keys are exact as they are in response. 
            ### details App Name: {app_name} App Categorie: {app_cat} App Sub Categorie: {app_sub_cat}

            ### Response format
            {response_format}
            """

response_format = '{"short_description": "this is short description", "long_description": "this is long description", ' \
                  '"short_feature": "this is short feature description", "keywords": "keyword1 keyword2 keyword3 ' \
                  'keyword4"}'


def get_chrome_driver(headless=False):
    driver = Driver(uc=True, incognito=True, headless=headless)
    driver.maximize_window()
    return driver


def get_static_filepath(static_path):
    """
    :param static_path:
    :return apk_filepath, img_512, img_114, ss
    """
    icon_512px = os.path.join(static_path, "Icon image_icon_512.png")
    icon_114px = os.path.join(static_path, "Icon image_icon_114.png")
    try:
        apk_filepath = [os.path.join(static_path, i) for i in os.listdir(static_path) if i.endswith(".apk")][0]
        screenshots = [os.path.join(static_path, i) for i in os.listdir(static_path) if i.startswith("Screenshot ")]
    except IndexError:
        logger.error("Apk file not found.. skipping..")
        raise IndexError
    data = {"icon_512": icon_512px, "icon_114": icon_114px,
            "screenshots_img": "\n".join(screenshots), "apk_filepath": apk_filepath}
    if not icon_114px and icon_512px and apk_filepath and screenshots:
        raise ValueError(f"unable to get all static files.. {data}")
    logger.debug(f"static files are {data}")
    return data


def get_descriptions(model, app_name, app_cat, app_sub_cat, retry=0):
    required_keys = ["short_description", "long_description", "short_feature", "keywords"]
    logger.debug(f"Generating descriptions for {app_name}")
    if not app_sub_cat:
        app_sub_cat = ""
    input_prompt = prompt.format(app_name=app_name, app_cat=app_cat, app_sub_cat=app_sub_cat,
                                 response_format=response_format)
    res = model.generate_content(input_prompt)
    try:
        res = json.loads(res.text.replace("\n", ""))
        if not all([True if i in res.keys() else False for i in required_keys]):
            logger.info(f"Did not get expected response from LLM, retrying again. retry count {retry} of 3")
            return get_descriptions(model, app_name, app_cat, app_sub_cat, retry=retry + 1)
    except json.JSONDecodeError:
        if retry < 3:
            logger.debug(f"unable to decode response to json, text response is {res.text}")
            return get_descriptions(model, app_name, app_cat, app_sub_cat, retry=retry+1)
        res = {"short_description": "Unable to generate short description",
               "long_description": "Unable to generate long description",
               "short_feature": "Unable to generate short feature",
               "keywords": "NA"}
    return res


def random_sleep(min_=1, max_=3):
    time.sleep(random.randint(min_, max_))


def start_typing(driver, elem, text):
    action = ActionChains(driver)
    action.move_to_element(elem).click()
    for i in text:
        action.send_keys(i)
        action.perform()
        time.sleep(random.uniform(0.2, 0.5))
    return True


def solve_captcha(driver):
    try:
        link = find_all(S("img", below="Enter the characters you see below"))[0].web_element.get_attribute("src")
    except IndexError:
        img = driver.find_element(By.XPATH, "//img[contains(@src, 'https://images-na.ssl-images-amazon.com/captcha')]")
        link = img.get_attribute("src")
    logger.debug(f"Extracted captcha link {link}")
    captcha = AmazonCaptcha.fromlink(link)
    text = captcha.solve(keep_logs=True)
    logger.debug(f"Solved captcha, solution text is {text}")
    write(text, into="Type characters")
    click(Button("Continue shopping"))
    return driver


def login(driver, email, password, totp, retry=0):
    totp_obj = pyotp.TOTP(totp)
    if retry < 1:
        driver.get(STATIC_DATA["dashboard_url"])
        random_sleep()

    captcha = driver.find_elements(By.XPATH, '//h4[contains(text(), "Enter the characters you see below")]')
    if captcha and retry < 3:
        logger.debug("Captcha detected, Solving captcha..")
        solve_captcha(driver)
        logger.debug(f"Retrying {retry} times to login")
        return login(driver, email, password, totp, retry=retry+1)

    logger.debug(f"entering email {email}")
    random_sleep(5, 10)
    window_handles = driver.window_handles
    driver.switch_to.window(window_handles[0])
    email_elem = driver.find_element(By.ID, "ap_email")
    start_typing(driver=driver, elem=email_elem, text=email)
    driver.find_element(By.ID, "continue").click()

    random_sleep(5, 10)
    logger.debug(f"entering password..")
    try:
        password_elem = driver.find_element(By.ID, "ap_password")
        start_typing(driver=driver, elem=password_elem, text=password)
    except NoSuchElementException:
        logger.info("unable to find password on first page, using login method 2")
        random_sleep(5, 10)
        driver.find_element(By.ID, "continue").click()
        random_sleep(5, 10)
        password_elem = driver.find_element(By.ID, "ap_password")
        start_typing(driver=driver, elem=password_elem, text=password)
    # write(password, into='password')
    driver.execute_script(STATIC_DATA["scroll_top_query"])
    logger.debug(f"Clicking signin button to login")
    random_sleep(5, 10)
    driver.find_element(By.ID, "signInSubmit").click()
    # click("sign in")
    random_sleep(5, 10)
    captcha = driver.find_elements(By.XPATH, '//h4[contains(text(), "Enter the characters you see below")]')
    if captcha:
        return login(driver, email, password, totp, retry=retry+1)

    if "/ap/mfa?ie=" in driver.current_url:
        logger.debug(f"entering MFA code")
        otp_elem = driver.find_element(By.ID, "auth-mfa-otpcode")
        start_typing(driver=driver, elem=otp_elem, text=totp_obj.now())
        # write(totp_obj.now(), into="Enter OTP")
    driver.execute_script(STATIC_DATA["scroll_top_query"])
    random_sleep(5, 10)
    logger.debug(f"Clicking signin button to login")
    driver.find_element(By.ID, "auth-signin-button").click()
    # click("sign in")
    random_sleep(5, 10)

    captcha = driver.find_elements(By.XPATH, '//h4[contains(text(), "Enter the characters you see below")]')
    if captcha and retry < 3:
        logger.debug("Captcha detected, Solving captcha..")
        solve_captcha(driver)
        logger.debug(f"Retrying {retry} times to login")
        return login(driver, email, password, totp, retry=retry+1)

    if "home" in driver.current_url:
        logger.debug("login success")
        return True
    elif "https://developer.amazon.com/500" in driver.current_url:
        logger.debug("account seems to be disabled by aws..")
    return False


def create_new_app(driver, app_name, app_category, app_sub_category, retry=0):
    logger.debug(f"Creating new app {app_name}")
    driver.get(STATIC_DATA["create_new_app_url"])
    random_sleep()

    try:
        write(app_name, into="App title")
        random_sleep()

        logger.debug(f"selecting category {app_category}")
        click(S('//*[@id="categoryLevel"]'))
        a = find_all(S(".sc-jIZahH.knFoqZ.sc-dwLEzm.ewuvWr"))[0]
        options_div = a.web_element.find_element(By.CSS_SELECTOR, ".sc-fEOsli.XZUkw.sc-hHLeRK.sc-iAvgwm.fPVxMZ.fmariK")
        for i in options_div.find_elements(By.CSS_SELECTOR, ".sc-cCsOjp.cbnA-Do"):
            if i.text.lower() == app_category.lower():
                logger.debug("found the element to select app category")
                click(i)
                break

        if app_sub_category:
            logger.debug(f"selecting sub category {app_sub_category}")
            random_sleep()
            click(S('//*[@id="subcategoryLevel"]'))
            a = find_all(S(".sc-jIZahH.knFoqZ.sc-dwLEzm.ewuvWr"))[1]
            options_div = a.web_element.find_element(By.CSS_SELECTOR, ".sc-fEOsli.XZUkw.sc-hHLeRK.sc-iAvgwm.fPVxMZ.fmariK")
            for i in options_div.find_elements(By.CSS_SELECTOR, ".sc-cCsOjp.cbnA-Do"):
                if i.text.lower() == app_sub_category.lower():
                    logger.debug("Found the element to select app sub category")
                    i.click()

        random_sleep()
        click("Save")
        logger.debug("Saved")
        random_sleep(min_=3, max_=5)
        if not driver.current_url.startswith("https://developer.amazon.com/apps-and-games/console/app/amzn1.devporta"):
            driver.refresh()
            logger.debug("The next page url did not change, retrying again..")
            return create_new_app(driver, app_name, app_category, app_sub_category, retry + 1)
        try:
            click("Looks Great")
        except LookupError:
            logger.error("Looks Great button not found, skipping to click..")
        return True
    except LookupError as e:
        if retry > 3:
            raise LookupError
        logger.error(f"Lookup error occurred, retrying {retry} again to create an app.")
        logger.debug(f"Error is {e}")
        driver.refresh()
        create_new_app(driver, app_name, app_category, app_sub_category, retry+1)


def create_app_page2(driver, static_path, game_features, language_support, retry=0, drm=True):
    try:
        apk_filepath = get_static_filepath(static_path)["apk_filepath"]
        logger.debug(f"apk filepath {apk_filepath}")
        random_sleep()
        for i in driver.find_elements(By.XPATH, '//*[@id="app-submissions-root"]//input'):
            if i.get_attribute("type") == "file":
                logger.debug("Uploading apk file")
                attach_file(apk_filepath, to=i)

        random_sleep()
        for lang in find_all(S(".orientation-right.css-z7vmfr", above="Language Support")):
            if lang.web_element.text == game_features:
                logger.debug(f"selecting game features to {game_features}")
                lang.web_element.click()
                break

        random_sleep()
        for lang in find_all(S(".orientation-right.css-z7vmfr", below="Language Support")):
            if lang.web_element.text == language_support:
                logger.debug(f"selecting supported language to {game_features}")
                lang.web_element.click()
                break

        logger.debug("Waiting for apk file to be uploaded.")
        for i in range(300):
            if find_all(S("//h5[text()='1 file(s) uploaded']")):
                logger.debug("Apk file uploaded..")
                break
            elif find_all(S(".react-toast-notifications__toast__content.css-1ad3zal")):
                raise AttributeError("Apk file already uploaded or amazon rejected. Skipping the current app..")
            random_sleep(min_=1, max_=2)

        random_sleep()
        try:
            if not drm:
                click(S("//label[@class='orientation-right css-qbmcu0']//span[text()='No']"))     # DRM No
            else:
                click(S("//label[@class='orientation-right css-qbmcu0']//span[text()='Yes']"))      # DRM Yes
        except:
            logger.info("DRM has no radio button..")

        random_sleep()
        driver.execute_script(STATIC_DATA["scroll_top_query"])
        random_sleep(min_=6, max_=10)
        next_button = driver.find_element(By.XPATH, "//button[text() = 'Next']")
        random_sleep()
        next_button.click()
        logger.debug("Clicked on Next button..")
    except LookupError as e:
        if retry > 3:
            raise LookupError
        logger.error(f"Lookup error occurred, retrying {retry} again page 2")
        logger.debug(f"Error is {e}")
        driver.refresh()
        create_app_page2(driver, static_path, game_features, language_support, retry=0)


def create_app_page3(driver, retry=0):
    try:
        logger.debug("filling details to page 3")
        random_sleep()
        # driver.find_element(By.XPATH, '//*[@id="target-audience-radio-group"]//input[@value="all"]').click()  # all age group
        driver.find_element(By.XPATH, "//input[@id='16-17 years of age']").click()     # check 16-17 age group
        random_sleep()
        driver.find_element(By.XPATH, '//input[@id="18+ years of age"]').click()    # check 18+ age group
        random_sleep()
        driver.find_element(By.XPATH, "//input[@name='collectPrivacyLabel'][@value='no']").click()

        random_sleep()
        click("View questionnaire")
        random_sleep()
        for i in driver.find_elements(By.XPATH, "//input[@aria-label='None' or @aria-label='No']"):
            i.click()
            time.sleep(0.5)

        try:
            random_sleep(min_=2, max_=5)
            scroll_up()
            driver.find_element(By.NAME, "content-attenuating-element-academic").click()
        except:
            logger.error("element NO is not clickable..")
        time.sleep(1)
        press(ESCAPE)
        random_sleep()

        driver.execute_script(STATIC_DATA["scroll_top_query"])
        random_sleep()
        driver.find_element(By.XPATH, "//button[text() = 'Next']").click()
        logger.debug("Completed page 3")
    except LookupError as e:
        if retry > 3:
            raise LookupError
        logger.error(f"Lookup error occurred, retrying {retry} again to page 3")
        logger.debug(f"Error is {e}")
        driver.refresh()
        create_app_page3(driver, retry+1)


def contains_in(text, lst):
    for i in lst:
        a = text.replace("\n", " ")
        if i in a:
            return True
    return False


def create_app_page4(driver, model, app_name, app_category, app_sub_category, static_path, price):
    random_sleep()

    if price:
        logger.info(f"Entering {price} price for {app_name}")
        input_radios = driver.find_elements(By.XPATH, "//input[@name='pricing_options']")
        click(input_radios[1])
        base_price = driver.find_element(By.XPATH, "//input[@name='base_price']")
        base_price.send_keys(price)
        logger.info(f"App price of {price} is set to {base_price}")

    data = get_descriptions(model, app_name, app_category, app_sub_category)
    logger.debug(f"Generated data - {data}")
    imgs = get_static_filepath(static_path)
    logger.debug(f"Static paths - {imgs}")
    write(data["short_description"], into="Short description")
    random_sleep()
    write(data["long_description"], into="Long description")
    random_sleep()
    write(data["short_feature"], into="Product feature bullets")
    random_sleep()
    write(data["keywords"], into="Add keywords")
    random_sleep()

    form = None
    for form in find_all(S("form")):
        h3 = form.web_element.find_element(By.TAG_NAME, "h3")
        if h3.text == "Images and videos":
            logger.debug("Found form with images and videos elements")
            break

    random_sleep()
    for i in form.web_element.find_elements(By.XPATH,
                                            "//div[@style='display: flex; gap: 0px; flex-direction: column; width: 50%;']"):

        # upload 512px
        random_sleep(min_=2, max_=4)
        try:
            if contains_in(i.text, ["512 x 512px PNG"]):
                logger.debug("Found 512p icon element to upload icon")
                attach_file(imgs["icon_512"], to=i.find_element(By.TAG_NAME, "input"))
                i.find_elements(By.TAG_NAME, "img")
        except NoSuchElementException:
            logger.debug("Unable to find 512px icon element")

        try:
            random_sleep(min_=2, max_=4)
            # upload 114px
            if contains_in(i.text, ["114 x 114px PNG"]):
                logger.debug("Found 114px icon element to upload icon")
                attach_file(imgs["icon_114"], to=i.find_element(By.TAG_NAME, "input"))
                i.find_elements(By.TAG_NAME, "img")
        except NoSuchElementException:
            logger.debug("Unable to find 114px element to upload icon")

        try:
            # upload screenshots
            random_sleep(min_=2, max_=4)
            if contains_in(i.text, ["Screenshots (minimum 3)"]):
                logger.debug("Found screenshot element to upload screenshots")
                attach_file(imgs["screenshots_img"], to=i.find_element(By.TAG_NAME, "input"))
                i.find_elements(By.TAG_NAME, "img")
        except NoSuchElementException:
            logger.error("Unable to find screenshot elements")
        random_sleep()

    for i in range(120):
        counter = 0
        for j in form.web_element.find_elements(By.XPATH,
                                                "//div[@style='display: flex; gap: 0px; flex-direction: column; width: 50%;']"):
            if j.find_elements(By.XPATH, "//img"):
                counter += 1
        if counter >= 3:
            logger.debug("all images present..")
            break
        counter = 0
        time.sleep(1)

    driver.execute_script(STATIC_DATA["scroll_top_query"])
    random_sleep()
    driver.find_element(By.XPATH, "//button[text() = 'Next']").click()
    logger.debug("Clicked on Next button")


def create_app_page5(driver):
    logger.debug("submitting final page")
    click("I certify this")
    # random_sleep()
    # publish_time = (datetime.now() + timedelta(hours=1.1)).strftime("%B %d, %Y %H:%M")
    # write(publish_time, into="Select a date")
    # random_sleep()
    # press(ENTER)
    random_sleep(min_=5, max_=10)
    submit_button = driver.find_element(By.XPATH, '//button[text()="Submit App"]')
    if not submit_button.is_enabled():
        logger.debug("Submit button is disabled, clicking on each image to revalidate the menus..")
        for i in range(4):
            menus = get_menu_elements(driver)
            menus[i].click()
            logger.debug(f"Clicked {i} menu")
            random_sleep(min_=2)

    try:
        logger.debug("Clicking on submit button..")
        submit_button = driver.find_element(By.XPATH, '//button[text()="Submit App"]')
        submit_button.click()
        logger.debug("App submitted..")
    except Exception as e:
        logger.error("App Submit button not clickable..")
        logger.debug(f"Exception is {e}")


def get_menu_elements(driver):
    allowed_menu = ["Upload your app file", "Target your app", "Appstore details", "Review & submit"]
    all_menus = driver.find_elements(By.XPATH, "//span[@class ='typography-t200']")
    menus = []
    for i in all_menus:
        if i.text in allowed_menu:
            menus.append(i)
    return menus


def modify_apk(apk_filename, new_package_name, package_dir):
    logger.debug("Modifying apk.")
    decompiled_filepath = str(os.path.join(package_dir, apk_filename.split(".")[0]))
    org_apk_filename = str(os.path.join(package_dir, apk_filename))
    decompile_apk(org_apk_filename, decompiled_filepath)
    change_package_name(decompiled_filepath, new_package_name)
    new_apk_filepath = compile_apk(decompiled_filepath, package_dir)
    try:
        shutil.rmtree(decompiled_filepath)
    except Exception as e:
        logger.error(f"Unable to remove decompiled folder.., {e}")
    logger.debug("Modifying apk done.")
    return new_apk_filepath


def get_running_status():
    with open(STATUS_FILEPATH, "r", encoding="utf-8") as file:
        status = file.read().strip()
    return status


def update_running_status(status):
    with open(STATUS_FILEPATH, "w", encoding="utf-8") as file:
        file.write(status)
    return True
