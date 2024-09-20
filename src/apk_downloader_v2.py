import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import parse_qsl
from pathlib import Path
import os
from logger import logger
from PIL import Image
from requests.exceptions import ChunkedEncodingError
from utils import get_chrome_driver

requests.packages.urllib3.disable_warnings()
WRK_DIR = Path(__file__).resolve().parents[1]
APK_DATA_PATH = os.path.join(WRK_DIR, "src", "apk_data")
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/89.0.4389.114 Safari/537.36",
}


def get_play_screenshots(play_url):
    response = requests.get(play_url, headers=headers, verify=False)
    soup = BeautifulSoup(response.text, "html.parser")
    try:
        name = soup.find("span", {"itemprop": "name"}).text
        urls = {"app_name": name}
        icon_img_url = soup.find("img", {"alt": "Icon image"}).get("src").split("=")[0]
        # "https://play-lh.googleusercontent.com/KxeSAjPTKliCErbivNiXrd6cTwfbqUJcbSRPe_IBVK_YmwckfMRS1VIHz-5cgT09yMo=w114-h114-rw"
        urls["Icon image_icon_114.png"] = icon_img_url + "=w114-h114-rp"
        urls["Icon image_icon_512.png"] = icon_img_url + "=w512-h512-rp"
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
    logger.info(f"Fetching apk downloading link {play_url}")
    package_name = get_package_name(play_url)
    url = get_apkpure_dl(play_url)
    if "winudf.com" in url:
        logger.info(f"Found apk download link from apkpure")
        logger.debug(f"download url is {url}")
        return url
    else:
        logger.info(f"Could not find apk download link from apkpure, trying again with apkcombo")
        ch_driver = get_chrome_driver(headless=True)
        try:
            search_url = f"https://apkcombo.com/downloader#package={package_name}"
            ch_driver.get(search_url)
            time.sleep(5)
            for i in range(10):
                time.sleep(3)
                soup = BeautifulSoup(ch_driver.page_source, "html.parser")
                apk_type = soup.find("ul", {"class": "file-list"}).find("span", {"class": "vtype"}).text.strip()
                if apk_type == "XAPK":
                    raise ValueError("APK type is XAPK, Skipping downloading..")
                download_link = soup.find("a", class_="variant").get("href")
                if download_link:
                    ch_driver.quit()
                    logger.info(f"Found apk download link from apkcombo")
                    logger.debug(f"download url is {download_link}")
                    return download_link
            ch_driver.quit()
            logger.info("Could not find the apk download link from apkcombo..")
        except Exception as e:
            logger.error(f"an exception occurred while fetching download link from apk combo, exception: {str(e)}")
            ch_driver.quit()
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


def download_apk_data(google_play_url, download_apk=True):
    logger.info(f"Downloading apk from {google_play_url}")
    package_name = get_package_name(google_play_url)
    logger.debug(f"Extracted the package name {package_name}")
    package_path = os.path.join(APK_DATA_PATH, package_name)
    if not os.path.exists(package_path):
        os.mkdir(package_path)
    data = get_play_screenshots(google_play_url)
    logger.debug(f"extracted all the apk data -- {data}")
    app_name = data.pop("app_name")
    if download_apk:
        apk_dl = get_apk_url(google_play_url)
        if not apk_dl:
            os.rmdir(package_path)
            return False, False
        data[f"{''.join(e for e in app_name if e.isalnum())}.apk"] = apk_dl
    for filename, url in data.items():
        download_n_save(url, filename, package_path)
    resize_images(package_path)
    return package_path, app_name


def download_n_save(url, filename, save_path_dir, retry=0):
    logger.debug(f"downloading {url}")
    filepath = os.path.join(save_path_dir, filename)

    with requests.get(url, stream=True, headers=headers, verify=False, timeout=30) as req:
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
            logger.debug(f"Failed to get data from {url}, retrying {retry + 1} time")
            download_n_save(url, filename, save_path_dir, retry=retry + 1)
    return filepath


# for test purpose.
# play_urls = """https://play.google.com/store/apps/details?id=com.egd.TheBaldEagleEscape
# https://play.google.com/store/apps/details?id=com.egd.FindTheAngelCrown
# https://play.google.com/store/apps/details?id=com.egd.HandsomeLittleBoyHouseEscape
# https://play.google.com/store/apps/details?id=com.egd.FunnyTomatoRescue
# https://play.google.com/store/apps/details?id=com.egd.ForestGreenTortoiseRescue
# https://play.google.com/store/apps/details?id=com.egd.GorgeousDalmatianDogHouseRescue
# https://play.google.com/store/apps/details?id=game.omicron.levelupsquad&ref=apkcombo.com
# https://play.google.com/store/apps/details?id=com.LinaGames.GlassMan&ref=apkcombo.com
# https://play.google.com/store/apps/details?id=game.omicron.climbwar&ref=apkcombo.com
# https://play.google.com/store/apps/details?id=com.acrab.matchitpuzzle&ref=apkcombo.com
# https://play.google.com/store/apps/details?id=com.toka.town.life.world.avatar.toca.boca.miga.toga.tira.my.world
# https://play.google.com/store/apps/details?id=com.Avatar.World.City.Life.tira.town.miga.toca.boca.Avitar
# https://play.google.com/store/apps/details?id=com.toka.town.life.world.avatar.toca.boca.miga.toga.tira.my.world.castle
# https://play.google.com/store/apps/details?id=com.anime.sakura.school.simulator.life.love.games
# https://play.google.com/store/apps/details?id=com.stair.run.bridge.race.bridgeway.game
# https://play.google.com/store/apps/details?id=com.diy.bubble.tea.tapioca.recipe.tasty
# https://play.google.com/store/apps/details?id=com.antistress.relaxing.games.stress.puppet
# https://play.google.com/store/apps/details?id=com.adnime.vlinder.princesss.dress.up.fashion.everskies.girl.games
# https://play.google.com/store/apps/details?id=com.love.nikki.adnime.dress.up.simulator.games
# https://play.google.com/store/apps/details?id=com.happy.township.farming.free.games
# https://play.google.com/store/apps/details?id=com.toka.hair.salon.makeup.games
# https://play.google.com/store/apps/details?id=com.ldle.market.tycoon.shopcooking
# https://play.google.com/store/apps/details?id=com.pranks.blastet.neaf.epic.game
# https://play.google.com/store/apps/details?id=com.anime.fashion.princess.girl.dress.up
# https://play.google.com/store/apps/details?id=com.world.war.mission.strikes.offline.game""".split("\n")
#
# #
# # with ThreadPoolExecutor(max_workers=5) as exe:
# #     for i in play_urls[:10]:
# #         data = download_apk_data(i)
# #         if not data:
# #             print("No data for ", i)
# #             continue
# #
# #         meta = data.pop("meta")
# #         results = exe.map(download_n_save, data.values(), data.keys(), [meta["package_path"]]*len(data))
# #         list(results)
#
# #
# a = []
# for i in play_urls:
#     print(f"downloading {i}")
#     link = get_apk_url(i)
#     print(f"link: {link}")
#     a.append(link)
#     print(f"Done downloading {i}")
# print(a)
