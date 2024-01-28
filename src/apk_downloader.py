import requests
from bs4 import BeautifulSoup
from urllib.parse import parse_qsl, urlunparse, urlparse, urlencode
from pathlib import Path
import os
from logger import logger

WRK_DIR = Path(__file__).resolve().parents[1]
APK_DATA_PATH = os.path.join(WRK_DIR, "src", "apk_data")


headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/89.0.4389.114 Safari/537.36"
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


def download_n_save(url, filename, save_path_dir):
    filepath = os.path.join(save_path_dir, filename)
    response = session.get(url)

    with open(filepath, "wb") as fp:
        fp.write(response.content)

    return filepath


def get_apk_image_urls(apk_page_url, package_name):
    apk_base_url = "https://d.apkpure.net/b/APK/{package_name}?version=latest"
    response = session.get(apk_page_url)
    soup = BeautifulSoup(response.content, "html.parser")
    apk_info_div = soup.find("div", class_="apk_info")
    app_name = soup.find("div", class_="title_link").text.strip()
    icon_url = apk_info_div.find("img").get("src")
    data = dict()
    data["Icon image_icon_114.png"] = urlunparse(urlparse(icon_url)._replace(query=urlencode({'fakeurl': '1', 'w': '114', 'type': '.png'})))
    data["Icon image_icon_512.png"] = urlunparse(urlparse(icon_url)._replace(query=urlencode({'fakeurl': '1', 'w': '512', 'type': '.png'})))
    screenshots_loc = soup.find("div", id="screen").find_all("a",  class_="screen-pswp")
    for i, ss in enumerate(screenshots_loc):
        data[f"Screenshot {i}.png"] = urlunparse(urlparse(ss.get("href"))._replace(query=urlencode({'fakeurl': '1', 'w': '720', 'type': '.png'})))
    data[f"{app_name}.apk"] = apk_base_url.format(package_name=package_name)
    return data


def download_apk_data(google_play_url):
    logger.info(f"Downloading apk from {google_play_url}")
    package_name = get_package_name(google_play_url)
    logger.debug(f"Extracted the package name {package_name}")
    package_path = os.path.join(APK_DATA_PATH, package_name)
    if not os.path.exists(package_path):
        os.mkdir(package_path)
    package_url = search_apk(package_name)
    data = get_apk_image_urls(package_url, package_name)
    logger.debug(f"extracted all the apk data -- {data}")
    for filename, url in data.items():
        logger.debug(f"downloading and saving file {filename} -- {url}")
        download_n_save(url, filename, package_path)
    logger.info(f"Saved the apk file and images in {package_name} folder.")
    return package_path
