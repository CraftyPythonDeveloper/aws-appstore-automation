import re
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
    response = requests.get(play_url, headers=headers)
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


def get_package_name(google_play_url):
    # example url https://play.google.com/store/apps/details?id=com.google.android.apps.photosgo
    return parse_qsl(google_play_url)[0][1]


ch_driver = get_chrome_driver()

def get_apk_url(play_url):
    pattern = r'/([^/]+)/$'
    package_name = get_package_name(play_url)
    try:
        search_url = f"https://apkcombo.com/search?q={package_name}"
        ch_driver.get(search_url)
        match = re.search(pattern, ch_driver.current_url)
        if match:
            download_url = f"https://apkcombo.com/{match.group(0)}/{package_name}/download/apk"
            ch_driver.get(download_url)
            time.sleep(5)
            soup = BeautifulSoup(ch_driver.page_source, "html.parser")
            download_link = soup.find("a", class_="variant").get("href")
            return download_link
        raise AttributeError
    except Exception as e:
        print(e)
        return f"https://d.apkpure.net/b/APK/{package_name}?version=latest"


play_urls = """https://play.google.com/store/apps/details?id=com.falcon.flying.TheEagleSimulator
https://play.google.com/store/apps/details?id=com.flying.squirrel.SquirrelSimulatorGame
https://play.google.com/store/apps/details?id=com.mane.jungle.hunter.FoxSimulator
https://play.google.com/store/apps/details?id=com.Hunter.world.KomodoDragonHuntingGame
https://play.google.com/store/apps/details?id=com.Sea.Queen.MermaidSimulatorGame
https://play.google.com/store/apps/details?id=com.Hungry.Wild.CrocodileSimulator
https://play.google.com/store/apps/details?id=com.Warthog.predator.hunter.PigSavannaWarthogGame
https://play.google.com/store/apps/details?id=com.Hunting.hot.jungle.BearhuntSimulator
https://play.google.com/store/apps/details?id=com.Hunter.Mane.TheWolfSimulator
https://play.google.com/store/apps/details?id=com.Insect.worm.SpiderSimulator
https://play.google.com/store/apps/details?id=com.Reptile.Venom.ScorpionSimulator
https://play.google.com/store/apps/details?id=com.Anaconda.Cobra.Ratle.SnakeSimulator
https://play.google.com/store/apps/details?id=com.Insect.Bug.AntSimulator
https://play.google.com/store/apps/details?id=com.bowandarrow.robbinhood.ArcheryMaster3D
https://play.google.com/store/apps/details?id=com.Xclusive.Pony.pet.FlyingUnicornSimulator
https://play.google.com/store/apps/details?id=com.rebirth.dragonhunt.DeadlyDragonRevengeSim
https://play.google.com/store/apps/details?id=com.King.Hunter.InsectoidCrabMonster
https://play.google.com/store/apps/details?id=com.Flying.Vampire.DuckSimulatorJungleGame
https://play.google.com/store/apps/details?id=com.Pridator.Aquatic.Swim.PiranhaUnderwaterGame
https://play.google.com/store/apps/details?id=com.parking.police.car
https://play.google.com/store/apps/details?id=com.parking.prado
https://play.google.com/store/apps/details?id=com.parking.oil.transport.truck
https://play.google.com/store/apps/details?id=com.parking.army.truck
https://play.google.com/store/apps/details?id=com.parking.buggy
https://play.google.com/store/apps/details?id=com.parking.crane.construction.truck
https://play.google.com/store/apps/details?id=com.parking.formula.car
https://play.google.com/store/apps/details?id=com.parking.emergency.ambulance.parking
https://play.google.com/store/apps/details?id=com.parking.hummer.prado
https://play.google.com/store/apps/details?id=com.parking.car.game
https://play.google.com/store/apps/details?id=com.parking.jeep
https://play.google.com/store/apps/details?id=com.parking.limousine.car
https://play.google.com/store/apps/details?id=com.parking.cargo.truck
https://play.google.com/store/apps/details?id=com.parking.transport.truck
https://play.google.com/store/apps/details?id=com.parking.ferrari
https://play.google.com/store/apps/details?id=com.parking.tuktuk.auto.rickshaw
https://play.google.com/store/apps/details?id=com.parking.tanks
https://play.google.com/store/apps/details?id=com.parking.american.police.van.driving
https://play.google.com/store/apps/details?id=com.parking.dump.truck
https://play.google.com/store/apps/details?id=com.parking.forklift.extreme
https://play.google.com/store/apps/details?id=com.parking.taxi.cab
https://play.google.com/store/apps/details?id=com.parking.log.transporter.truck
https://play.google.com/store/apps/details?id=com.parking.tractor
https://play.google.com/store/apps/details?id=com.parking.fire.fighter.truck
https://play.google.com/store/apps/details?id=com.parking.bus
https://play.google.com/store/apps/details?id=com.parking.euro.truck
https://play.google.com/store/apps/details?id=com.parking.quad.bike
https://play.google.com/store/apps/details?id=com.parking.police.bus
https://play.google.com/store/apps/details?id=com.parking.monster.truck
https://play.google.com/store/apps/details?id=com.parking.pickup.truck""".split("\n")


download_url = []
for i in play_urls:
    download_url.append(get_apk_url(i))

print(download_url)

ch_driver.close()
