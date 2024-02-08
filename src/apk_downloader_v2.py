import re
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

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

requests.packages.urllib3.disable_warnings()
WRK_DIR = Path(__file__).resolve().parents[1]
APK_DATA_PATH = os.path.join(WRK_DIR, "src", "apk_data")
py_downloader = Downloader()
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/89.0.4389.114 Safari/537.36",
}


def get_chrome_driver(headless=False):
    chrome_options = ChromeOptions()
    if headless:
        chrome_options.add_argument("--headless")
    driver = Chrome(options=chrome_options)
    driver.maximize_window()
    return driver


def get_play_screenshots(play_url):
    response = requests.get(play_url, headers=headers, verify=False)
    soup = BeautifulSoup(response.text, "html.parser")
    try:
        name = soup.find("h1", {"itemprop": "name"}).text
        urls = {"app_name": name}
        for url_soup in soup.find("div", {"jsname": "K9a4Re"}).find_all("img"):
            if len(urls) >= 9:
                break
            urls[f"Screenshot {len(urls)}.png"] = url_soup.get("src").split("=")[0]
        # print(name, urls)
        return urls
    except AttributeError:
        return False


def get_package_name(google_play_url):
    # example url https://play.google.com/store/apps/details?id=com.google.android.apps.photosgo
    return parse_qsl(google_play_url)[0][1]


def get_apkpure_dl(play_url):
    base_url = f"https://d.apkpure.net/b/APK/{get_package_name(play_url)}?version=latest"
    res = requests.head(base_url, verify=False)
    return res.headers["Location"]


def get_apk_url(play_url):
    pattern = r'/([^/]+)/$'
    package_name = get_package_name(play_url)
    url = get_apkpure_dl(play_url)
    if "winudf.com" in url:
        return url
    else:
        ch_driver = get_chrome_driver()
        try:
            search_url = f"https://apkcombo.com/search?q={package_name}"
            ch_driver.get(search_url)
            time.sleep(5)
            match = re.search(pattern, ch_driver.current_url)
            if match:
                download_url = f"https://apkcombo.com/{match.group(0)}/{package_name}/download/apk"
                ch_driver.get(download_url)
                time.sleep(5)
                soup = BeautifulSoup(ch_driver.page_source, "html.parser")
                download_link = soup.find("a", class_="variant").get("href")
                ch_driver.close()
                return download_link
        except Exception as e:
            print(e)
            ch_driver.close()
        return False


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


def download_apk_data(google_play_url):
    logger.info(f"Downloading apk from {google_play_url}")
    package_name = get_package_name(google_play_url)
    logger.debug(f"Extracted the package name {package_name}")
    package_path = os.path.join(APK_DATA_PATH, package_name)
    if not os.path.exists(package_path):
        os.mkdir(package_path)
    data = get_play_screenshots(google_play_url)
    logger.debug(f"extracted all the apk data -- {data}")
    apk_dl = get_apk_url(google_play_url)
    if not apk_dl:
        os.rmdir(package_path)
        return False
    data[f"{''.join(e for e in data['app_name'] if e.isalnum())}.apk"] = apk_dl
    # data["meta"] = {"package_path": package_path, "package_name": package_name, "app_name": data.pop("app_name")}
    # meta = data.pop("meta")
    app_name = data.pop("app_name")
    for filename, url in data.items():
        download_n_save(url, filename, package_path)
    resize_images(package_path)
    return app_name, package_path

    #
    # results = exe.map(download_n_save, data.values(), data.keys(), [meta["package_path"]] * len(data))
    # list(results)

    # return data


def download_n_save(url, filename, save_path_dir, retry = 0):
    logger.debug(f"downloading {url}")
    filepath = os.path.join(save_path_dir, filename)

    with requests.get(url, stream=True, headers=headers, verify=False) as req:
        if not req.ok:
            logger.error(f"unable to download {filename} file..")
            req.raise_for_status()
        try:
            with open(filepath, "wb") as fp:
                for data in req.iter_content(chunk_size=8192):
                    fp.write(data)
        except ChunkedEncodingError as e:
            if retry > 1:
                os.remove(filepath)
                logger.debug(f"unable to download from {url} after retrying {retry} times.")
                return ""
            logger.debug(f"Failed to get data from {url}, retrying {retry+1} time")
            download_n_save(url, filename, save_path_dir, retry=retry+1)
    return filepath


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
# with ThreadPoolExecutor(max_workers=5) as exe:
#     for i in play_urls[:10]:
#         data = download_apk_data(i)
#         if not data:
#             print("No data for ", i)
#             continue
#
#         meta = data.pop("meta")
#         results = exe.map(download_n_save, data.values(), data.keys(), [meta["package_path"]]*len(data))
#         list(results)

#
# for i in play_urls:
#     print(f"downloading {i}")
#     download_apk_data(i)
#     print(f"Done downloading {i}")