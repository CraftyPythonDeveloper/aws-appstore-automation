import time
from concurrent.futures import ThreadPoolExecutor

import requests
from bs4 import BeautifulSoup
from urllib.parse import parse_qsl, urlunparse, urlparse, urlencode
from pathlib import Path
import os
from logger import logger
from PIL import Image
from selenium.webdriver import Chrome, ChromeOptions
from requests.exceptions import ChunkedEncodingError, ConnectionError
from pypdl import Downloader


WRK_DIR = Path(__file__).resolve().parents[1]
APK_DATA_PATH = os.path.join(WRK_DIR, "src", "apk_data")
py_downloader = Downloader()
chrome_options = ChromeOptions()
chrome_options.add_argument("--headless")
driver = Chrome()
driver.maximize_window()

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/89.0.4389.114 Safari/537.36",
    "referer": 'https://apkpure.net/'
}
session = requests.Session()
session.headers = headers


def get_package_name(google_play_url):
    # example url https://play.google.com/store/apps/details?id=com.google.android.apps.photosgo
    return parse_qsl(google_play_url)[0][1]


def search_apk(query):
    url = f"https://apkpure.net/search?q={query}"
    response = session.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    return soup.find("a", class_="first-info").get("href")


def download_n_save(url, filename, save_path_dir, retry=0):
    logger.debug(f"downloading {url}")
    filepath = os.path.join(save_path_dir, filename)

    multithread = False
    if filename.endswith(".apk"):
        multithread = True

    py_downloader.start(url, file_path=filepath, multithread=multithread, retries=3, display=False)

    # with requests.get(url, stream=True, allow_redirects=True, headers=headers) as req:
    #     if not req.ok:
    #         logger.error(f"unable to download {filename} file..")
    #         req.raise_for_status()
    #     try:
    #         with open(filepath, "wb") as fp:
    #             for data in req.iter_content(chunk_size=8192):
    #                 fp.write(data)
    #     except ChunkedEncodingError as e:
    #         if retry > 3:
    #             os.remove(filepath)
    #             logger.debug(f"unable to download from {url} after retrying 3 times.")
    #             return ""
    #         logger.debug(f"Failed to get data from {url}, retrying {retry+1} time")
    #         download_n_save(url, filename, save_path_dir, retry=retry+1)
    return filepath


def resize_images(img_dir):
    imgs = [os.path.join(img_dir, file) for file in os.listdir(img_dir) if file.endswith(".png") and "Icon" not in file]

    for image in imgs:
        img = Image.open(image)
        width, height = img.size
        if width > height:
            new_size = (1280, 720)
        else:
            new_size = (720, 1280)
        try:
            resized_img = img.resize(new_size, Image.BICUBIC)
            resized_img.save(image)
        except Exception as e:
            img.close()
            logger.debug(f"error while resizing image. Error is ==> {str(e)}")
            os.remove(image)


def get_apk_image_urls(apk_page_url, package_name):
    apk_base_url = "https://d.apkpure.net/b/APK/{package_name}?version=latest"
    response = session.get(apk_page_url)
    soup = BeautifulSoup(response.content, "html.parser")
    apk_info_div = soup.find("div", class_="apk_info")
    app_name = soup.find("div", class_="title_link").text.strip()
    icon_url = apk_info_div.find("img").get("src")
    data = dict()
    data[f"{''.join(e for e in app_name if e.isalnum())}.apk"] = apk_base_url.format(package_name=package_name)
    data["Icon image_icon_114.png"] = urlunparse(urlparse(icon_url)._replace(query=urlencode({'fakeurl': '1', 'w': '114', 'type': '.png'})))
    data["Icon image_icon_512.png"] = urlunparse(urlparse(icon_url)._replace(query=urlencode({'fakeurl': '1', 'w': '512', 'type': '.png'})))
    screenshots_loc = soup.find("div", id="screen").find_all("a",  class_="screen-pswp")
    for i, ss in enumerate(screenshots_loc):
        data[f"Screenshot {i}.png"] = urlunparse(urlparse(ss.get("href"))._replace(query=urlencode(
            {'fakeurl': '1', 'type': '.png'})))
    return data, app_name


def get_apk_url_apkcombo(package_name):
    url = "https://apkcombo.com/autokill-sandbox/{package_name}/download/apk"
    driver.get(url.format(package_name=package_name))
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    download_link = soup.find("a", class_="variant").get("href")
    driver.close()
    logger.debug(f"Extracted download url from apkcombo {download_link}")
    return download_link


def get_play_screenshots(play_url):
    response = requests.get(play_url)
    soup = BeautifulSoup(response.text, "html.parser")
    try:
        name = soup.find("h1", {"itemprop": "name"}).text
        urls = dict()
        for url_soup in soup.find("div", {"jsname": "K9a4Re"}).find_all("img"):
            if len(urls) >= 9:
                break
            urls[f"Screenshot {len(urls)}.png"] = url_soup.get("src").split("=")[0]
        print(name, urls)
        return name, urls
    except AttributeError:
        return False

def get_apk_download_url(package_name):
    try:
        apk_url = get_apk_url_apkcombo(package_name)
    except Exception as e:
        print(e)
        apk_url = f"https://d.apkpure.net/b/APK/{package_name}?version=latest"
    return apk_url


def download_apk_data(google_play_url):
    logger.info(f"Downloading apk from {google_play_url}")
    package_name = get_package_name(google_play_url)
    logger.debug(f"Extracted the package name {package_name}")
    package_path = os.path.join(APK_DATA_PATH, package_name)
    if not os.path.exists(package_path):
        os.mkdir(package_path)
    app_name, data = get_play_screenshots(google_play_url)
    logger.debug(f"extracted all the apk data -- {data}")

    with ThreadPoolExecutor(max_workers=4) as executor:
        data = executor.map(download_helper, data.values(), data.keys(), [package_path]*len(data.values()), [package_name]*len(data.values()))
        list(data)

    resize_images(package_path)
    logger.info(f"Saved the apk file and images in {package_name} folder.")
    return package_path, app_name


def download_helper(url, filename, package_path, package_name):
    """
    a helper function to make downloading process run in thread
    """
    logger.debug(f"downloading and saving file {filename} -- {url}")

    try:
        download_n_save(url, filename, package_path)
    except ConnectionError:
        if not filename.endswith(".apk"):
            raise ConnectionError
        logger.debug("Attempting to download apk using alternate mirror site..")
        url = get_apk_url_apkcombo(package_name)
        download_n_save(url, filename, package_path)
    return True

#  below code is for Testing
# play_urls = """https://play.google.com/store/apps/details?id=com.falcon.flying.TheEagleSimulator
# https://play.google.com/store/apps/details?id=com.flying.squirrel.SquirrelSimulatorGame
# https://play.google.com/store/apps/details?id=com.mane.jungle.hunter.FoxSimulator
# https://play.google.com/store/apps/details?id=com.Hunter.world.KomodoDragonHuntingGame
# https://play.google.com/store/apps/details?id=com.Sea.Queen.MermaidSimulatorGame
# https://play.google.com/store/apps/details?id=com.Hungry.Wild.CrocodileSimulator
# https://play.google.com/store/apps/details?id=com.Warthog.predator.hunter.PigSavannaWarthogGame
# https://play.google.com/store/apps/details?id=com.Hunting.hot.jungle.BearhuntSimulator
# https://play.google.com/store/apps/details?id=com.Hunter.Mane.TheWolfSimulator
# https://play.google.com/store/apps/details?id=com.Insect.worm.SpiderSimulator
# https://play.google.com/store/apps/details?id=com.Reptile.Venom.ScorpionSimulator
# https://play.google.com/store/apps/details?id=com.Anaconda.Cobra.Ratle.SnakeSimulator
# https://play.google.com/store/apps/details?id=com.Insect.Bug.AntSimulator
# https://play.google.com/store/apps/details?id=com.bowandarrow.robbinhood.ArcheryMaster3D
# https://play.google.com/store/apps/details?id=com.Xclusive.Pony.pet.FlyingUnicornSimulator
# https://play.google.com/store/apps/details?id=com.rebirth.dragonhunt.DeadlyDragonRevengeSim
# https://play.google.com/store/apps/details?id=com.King.Hunter.InsectoidCrabMonster
# https://play.google.com/store/apps/details?id=com.Flying.Vampire.DuckSimulatorJungleGame
# https://play.google.com/store/apps/details?id=com.Pridator.Aquatic.Swim.PiranhaUnderwaterGame
# https://play.google.com/store/apps/details?id=com.parking.police.car
# https://play.google.com/store/apps/details?id=com.parking.prado
# https://play.google.com/store/apps/details?id=com.parking.oil.transport.truck
# https://play.google.com/store/apps/details?id=com.parking.army.truck
# https://play.google.com/store/apps/details?id=com.parking.buggy
# https://play.google.com/store/apps/details?id=com.parking.crane.construction.truck
# https://play.google.com/store/apps/details?id=com.parking.formula.car
# https://play.google.com/store/apps/details?id=com.parking.emergency.ambulance.parking
# https://play.google.com/store/apps/details?id=com.parking.hummer.prado
# https://play.google.com/store/apps/details?id=com.parking.car.game
# https://play.google.com/store/apps/details?id=com.parking.jeep
# https://play.google.com/store/apps/details?id=com.parking.limousine.car
# https://play.google.com/store/apps/details?id=com.parking.cargo.truck
# https://play.google.com/store/apps/details?id=com.parking.transport.truck
# https://play.google.com/store/apps/details?id=com.parking.ferrari
# https://play.google.com/store/apps/details?id=com.parking.tuktuk.auto.rickshaw
# https://play.google.com/store/apps/details?id=com.parking.tanks
# https://play.google.com/store/apps/details?id=com.parking.american.police.van.driving
# https://play.google.com/store/apps/details?id=com.parking.dump.truck
# https://play.google.com/store/apps/details?id=com.parking.forklift.extreme
# https://play.google.com/store/apps/details?id=com.parking.taxi.cab
# https://play.google.com/store/apps/details?id=com.parking.log.transporter.truck
# https://play.google.com/store/apps/details?id=com.parking.tractor
# https://play.google.com/store/apps/details?id=com.parking.fire.fighter.truck
# https://play.google.com/store/apps/details?id=com.parking.bus
# https://play.google.com/store/apps/details?id=com.parking.euro.truck
# https://play.google.com/store/apps/details?id=com.parking.quad.bike
# https://play.google.com/store/apps/details?id=com.parking.police.bus
# https://play.google.com/store/apps/details?id=com.parking.monster.truck
# https://play.google.com/store/apps/details?id=com.parking.pickup.truck""".split("\n")
#
# for i in play_urls:
#     download_apk_data(i)
