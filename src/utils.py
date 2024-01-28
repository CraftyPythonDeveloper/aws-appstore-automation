import json
import os.path
import random
import time

from helium import *
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from datetime import datetime, timedelta
from logger import logger
from amazoncaptcha import AmazonCaptcha
import pyotp


STATIC_DATA = {
    "dashboard_url": "https://developer.amazon.com/dashboard",
    "create_new_app_url": "https://developer.amazon.com/apps-and-games/console/app/new.html",
    "scroll_top_query": "document.documentElement.scrollTop = 0;",
    "logout_url": "https://www.amazon.com/ap/signin?openid.return_to=https%3A%2F%2Fdeveloper.amazon.com%2Fapps-and"
                  "-games&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid"
                  ".assoc_handle=mas_dev_portal&openid.mode=logout&openid.claimed_id=http%3A%2F%2Fspecs.openid.net"
                  "%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0&language"
                  "=en_US",

}
prompt = """You are an android app description suggestion agent and your job is to generate short description, 
            long description and short feature description of android app by using below provided details and make sure to use 
            response format as reference to provide response in the same key value pair, the key name should be strictly followed. 
            ### details App Name: {app_name} App Categorie: {app_cat} App Sub Categorie: {app_sub_cat}

            ### Response format
            {response_format}
            """

response_format = '{"short_description": "this is short description", "long_description": "this is long description", ' \
                  '"short_feature": "this is short feature description", "keywords": "keyword1 keyword2 keyword3 ' \
                  'keyword4"}'


def get_static_filepath(static_path):
    """
    :param static_path:
    :return apk_filepath, img_512, img_114, ss
    """
    icon_512px = os.path.join(static_path, "Icon image_icon_512.png")
    icon_114px = os.path.join(static_path, "Icon image_icon_114.png")
    apk_filepath = [os.path.join(static_path, i) for i in os.listdir(static_path) if i.endswith(".apk")][0]
    screenshots = [os.path.join(static_path, i) for i in os.listdir(static_path) if i.startswith("Screenshot ")]
    data = {"icon_512": icon_512px, "icon_114": icon_114px,
            "screenshots_img": "\n".join(screenshots), "apk_filepath": apk_filepath}
    if not icon_114px and icon_512px and apk_filepath and screenshots:
        raise ValueError(f"unable to get all static files.. {data}")
    logger.debug(f"static files are {data}")
    return data


def get_descriptions(model, app_name, app_cat, app_sub_cat, retry=0):
    logger.debug(f"Generating descriptions for {app_name}")
    input_prompt = prompt.format(app_name=app_name, app_cat=app_cat, app_sub_cat=app_sub_cat,
                                 response_format=response_format)
    res = model.generate_content(input_prompt)
    try:
        res = json.loads(res.text.replace("\n", ""))
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
    write(email, into='email')
    random_sleep()
    logger.debug(f"entering password..")
    write(password, into='password')
    driver.execute_script(STATIC_DATA["scroll_top_query"])
    logger.debug(f"Clicking signin button to login")
    click("sign in")
    random_sleep()
    if "/ap/mfa?ie=" in driver.current_url:
        logger.debug(f"entering MFA code")
        write(totp_obj.now(), into="Enter OTP")
    driver.execute_script(STATIC_DATA["scroll_top_query"])
    random_sleep()
    logger.debug(f"Clicking signin button to login")
    click("sign in")
    random_sleep()
    if "home" in driver.current_url:
        logger.debug("login success")


def create_new_app(driver, app_name, app_category, app_sub_category):
    logger.debug(f"Creating new app {app_name}")
    driver.get(STATIC_DATA["create_new_app_url"])
    random_sleep()

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
        logger.debug("Error occurred while submitting..")
        raise AttributeError("Error occurred while submitting..")
    try:
        click("Looks Great")
    except LookupError:
        logger.debug("Unable to find looks great button..")
    return True


def create_app_page2(driver, static_path, game_features, language_support):
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
            raise AttributeError("Apk file already uploaded. Skipping the current app..")
        random_sleep(min_=1, max_=2)

    random_sleep()
    # click(S("//label[@class='orientation-right css-qbmcu0']//span[text()='No']"))     # DRM No
    click(S("//label[@class='orientation-right css-qbmcu0']//span[text()='Yes']"))      # DRM Yes

    random_sleep()
    driver.execute_script(STATIC_DATA["scroll_top_query"])
    random_sleep()
    driver.find_element(By.XPATH, "//button[text() = 'Next']").click()
    logger.debug("Clicked on Next button..")


def create_app_page3(driver):
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

    random_sleep(min_=2, max_=5)
    driver.find_element(By.NAME, "content-attenuating-element-academic").click()
    time.sleep(1)
    press(ESCAPE)
    random_sleep()

    driver.execute_script(STATIC_DATA["scroll_top_query"])
    random_sleep()
    driver.find_element(By.XPATH, "//button[text() = 'Next']").click()
    logger.debug("Completed page 3")


def contains_in(text, lst):
    for i in lst:
        a = text.replace("\n", " ")
        if i in a:
            return True
    return False


def create_app_page4(driver, model, app_name, app_category, app_sub_category, static_path):
    random_sleep()
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
    random_sleep()
    publish_time = (datetime.now() + timedelta(hours=1.1)).strftime("%B %d, %Y %H:%M")
    write(publish_time, into="Select a date")
    random_sleep()
    press(ENTER)
    random_sleep(min_=5, max_=10)
    submit_button = driver.find_element(By.XPATH, '//button[text()="Submit App"]')
    if not submit_button.is_enabled():
        logger.debug("Submit button is disabled, clicking on each image to revalidate the menus..")
        for i in range(4):
            menus = get_menu_elements(driver)
            menus[i].click()
            logger.debug(f"Clicked {i} menu")
            random_sleep(min_=2)
    logger.debug("Clicking on submit button..")
    submit_button = driver.find_element(By.XPATH, '//button[text()="Submit App"]')
    submit_button.click()
    logger.debug("App submitted..")


def get_menu_elements(driver):
    allowed_menu = ["Upload your app file", "Target your app", "Appstore details", "Review & submit"]
    all_menus = driver.find_elements(By.XPATH, "//span[@class ='typography-t200']")
    menus = []
    for i in all_menus:
        if i.text in allowed_menu:
            menus.append(i)
    return menus
