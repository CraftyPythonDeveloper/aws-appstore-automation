import json
import os.path
import random
import time

from helium import *
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from datetime import datetime, timedelta
from exceptions import LoginError

STATIC_DATA = {
                "dashboard_url": "https://developer.amazon.com/dashboard",
                "create_new_app_url": "https://developer.amazon.com/apps-and-games/console/app/new.html",
                "scroll_top_query": "document.documentElement.scrollTop = 0;",

}
prompt = """You are an android app description suggestion agent and your job is to generate short description, 
            long description and short feature description of android app by using below provided details and make sure to use 
            response format as refrence to provide response in the same key value pair, the key name should be strictly followed. 
            ### details App Name: {app_name} App Categorie: {app_cat} App Sub Categorie: {app_sub_cat}

            ### Response format
            {response_format}
            """

response_format = '{"short_description": "this is short description", "long_description": "this is long description", '\
                  '"short_feature": "this is short feature description", "keywords": "keyword1 keyword2 keyword3 ' \
                  'keyword4"}'


def get_static_filepath(static_path):
    "return apk_filepath, img_512, img_114, ss"
    # imgs = {"icon_512": img_512, "icon_114": img_114,
    #         "screenshots_img": screenshots}
    icon_512px = os.path.join(static_path, "Icon image_icon_512.png")
    icon_114px = os.path.join(static_path, "Icon image_icon_114.png")
    apk_filepath = [os.path.join(static_path, i) for i in os.listdir(static_path) if i.endswith(".apk")][0]
    screenshots = [i for i in os.listdir(static_path) if i.startswith("Screenshot ")]
    data = {"icon_512": icon_512px, "icon_114": icon_114px,
            "screenshots_img": "\n".join(screenshots), "apk_file": apk_filepath}
    return data


def get_descriptions(model, app_name, app_cat, app_sub_cat):
    input_prompt = prompt.format(app_name=app_name, app_cat=app_cat, app_sub_cat=app_sub_cat,
                                 response_format=response_format)
    res = model.generate_content(input_prompt)
    try:
        res = json.loads(res.text.replace("\n", ""))
    except json.JSONDecodeError:
        res = {"short_description": "Unable to generate short description",
               "long_description": "Unable to generate long description",
               "short_feature": "Unable to generate short feature",
               "keywords": "NA"}
    return res


def random_sleep(min_=1, max_=3):
    time.sleep(random.randint(min_, max_))


def login(driver, email, password, totp):
    try:
        driver.get(STATIC_DATA["dashboard_url"])
        random_sleep()
        write(email, into='email')
        random_sleep()
        write(password, into='password')
        driver.execute_script(STATIC_DATA["scroll_top_query"])
        click("sign in")
        random_sleep()
        if "/ap/mfa?ie=" in driver.current_url:
            write(totp.now(), into="Enter OTP")
        driver.execute_script(STATIC_DATA["scroll_top_query"])
        random_sleep()
        click("sign in")
        random_sleep()
        if "home" in driver.current_url:
            print("login success")
    except Exception:
        raise LoginError


def create_new_app(driver, app_name, app_category, app_sub_category):
    driver.get(STATIC_DATA["create_new_app_url"])
    random_sleep()
    write(app_name, into="App title")
    random_sleep()
    click(S('//*[@id="categoryLevel"]'))
    a = find_all(S(".sc-jIZahH.knFoqZ.sc-dwLEzm.ewuvWr"))[0]
    options_div = a.web_element.find_element(By.CSS_SELECTOR, ".sc-fEOsli.XZUkw.sc-hHLeRK.sc-iAvgwm.fPVxMZ.fmariK")
    for i in options_div.find_elements(By.CSS_SELECTOR, ".sc-cCsOjp.cbnA-Do"):
        if i.text.lower() == app_category.lower():
            click(i)

    random_sleep()
    click(S('//*[@id="subcategoryLevel"]'))
    a = find_all(S(".sc-jIZahH.knFoqZ.sc-dwLEzm.ewuvWr"))[1]
    options_div = a.web_element.find_element(By.CSS_SELECTOR, ".sc-fEOsli.XZUkw.sc-hHLeRK.sc-iAvgwm.fPVxMZ.fmariK")
    for i in options_div.find_elements(By.CSS_SELECTOR, ".sc-cCsOjp.cbnA-Do"):
        if i.text.lower() == app_sub_category.lower():
            i.click()

    random_sleep()
    click("Save")
    random_sleep(min_=3, max_=5)
    if not driver.current_url.startswith("https://developer.amazon.com/apps-and-games/console/app/amzn1.devporta"):
        raise AttributeError("Error occurred while submitting..")
    try:
        click("Looks Great")
    except LookupError:
        pass
    return True


def create_app_page2(driver, static_path, game_features, language_support):
    apk_filepath = get_static_filepath(static_path)["apk_filepath"]
    random_sleep()
    for i in driver.find_elements(By.XPATH, '//*[@id="app-submissions-root"]//input'):
        if i.get_attribute("type") == "file":
            attach_file(apk_filepath, to=i)

    random_sleep()
    for lang in find_all(S(".orientation-right.css-z7vmfr", above="Language Support")):
        if lang.web_element.text == game_features:
            print(lang.web_element.text)
            click(lang)

    random_sleep()
    for lang in find_all(S(".orientation-right.css-z7vmfr", below="Language Support")):
        if lang.web_element.text == language_support:
            print(lang.web_element.text)
            click(lang)

    for i in range(300):
        if find_all(S("//h5[text()='1 file(s) uploaded']")):
            break
        random_sleep(min_=1, max_=2)

    random_sleep()
    click(S("//label[@class='orientation-right css-qbmcu0']//span[text()='No']"))

    random_sleep()
    driver.execute_script(STATIC_DATA["scroll_top_query"])
    random_sleep()
    click(Button("Next"))


def create_app_page3(driver):
    random_sleep()
    for i in find_all(S(".orientation-right.css-qbmcu0")):
        if i.web_element.text == "All age groups":
            print(i.web_element.text)
            click(i)

    random_sleep()
    for i in driver.find_elements(By.XPATH, "//input[@name='collectPrivacyLabel']"):
        if i.get_attribute("value") == "no":
            click(i)

    random_sleep()
    click("View questionnaire")
    random_sleep()
    for i in driver.find_elements(By.XPATH, "//input[@aria-label='None' or @aria-label='No']"):
        click(i)
        time.sleep(0.5)

    random_sleep()
    click(driver.find_element(By.NAME, "content-attenuating-element-academic"))
    time.sleep(1)
    press(ESCAPE)
    random_sleep()

    driver.execute_script(STATIC_DATA["scroll_top_query"])
    random_sleep()
    click(Button("Next"))


def contains_in(text, lst):
    for i in lst:
        a = text.replace("\n", " ")
        print(a)
        if i in a:
            return True
    return False


def create_app_page4(driver, model, app_name, app_category, app_sub_category, static_path):

    random_sleep()
    data = get_descriptions(model, app_name, app_category, app_sub_category)
    imgs = get_static_filepath(static_path)

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
            print(h3.text)
            break

    random_sleep()
    for i in form.web_element.find_elements(By.XPATH,
            "//div[@style='display: flex; gap: 0px; flex-direction: column; width: 50%;']"):

        # upload 512px
        random_sleep(min_=2, max_=4)
        try:
            if contains_in(i.text, ["512 x 512px PNG"]):
                attach_file(imgs["icon_512"], to=i.find_element(By.TAG_NAME, "input"))
                i.find_elements(By.TAG_NAME, "img")
        except NoSuchElementException:
            print("512")

        try:
            random_sleep(min_=2, max_=4)
            # upload 114px
            if contains_in(i.text, ["114 x 114px PNG"]):
                attach_file(imgs["icon_114"], to=i.find_element_by_tag_name("input"))
                i.find_elements(By.TAG_NAME, "img")
        except NoSuchElementException:
            print("114")

        try:
            # upload screenshots
            random_sleep(min_=2, max_=4)
            if contains_in(i.text, ["Screenshots (minimum 3)"]):
                img_filepaths = "\n".join(imgs["screenshots_img"])
                attach_file(img_filepaths, to=i.find_element_by_tag_name("input"))
                i.find_elements(By.TAG_NAME, "img")
        except NoSuchElementException:
            print("ss")
        random_sleep()

    for i in range(120):
        counter = 0
        for j in form.web_element.find_elements(By.XPATH,
             "//div[@style='display: flex; gap: 0px; flex-direction: column; width: 50%;']"):
            if j.find_elements(By.XPATH, "img"):
                counter += 1
        if counter >= 3:
            print("all images present..")
            break
        counter = 0
        time.sleep(1)

    driver.execute_script(STATIC_DATA["scroll_top_query"])
    random_sleep()
    click(Button("Next"))


def create_app_page5(driver):
    click("I certify this")
    random_sleep()
    publish_time = (datetime.now() + timedelta(hours=1.1)).strftime("%B %d, %Y %H:%M")
    write(publish_time, into="Select a date")
    random_sleep()
    press(ENTER)
