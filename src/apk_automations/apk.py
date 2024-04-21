import subprocess
import sys
from pathlib import Path
import os
from xml.etree import ElementTree

sys.path.append("..")

from logger import logger

SRC_DIR = Path(__file__).resolve().parents[1]
APKTOOL_FILE = os.path.join(SRC_DIR, 'apk_automations', "apktools", "apktool.jar")
APK_SIGNER = os.path.join(SRC_DIR, 'apk_automations', "apktools", "apksigner.jar")
ZIP_ALIGN_FILE = os.path.join(SRC_DIR, 'apk_automations', "apktools", "zipalign.exe")
APKTOOL_PATH = os.path.join(SRC_DIR, 'apk_automations', "apktools")


def decompile_apk(apk_filepath: str, decompiled_apk_filepath: str) -> str:
    """
    Decompile an apk
    :param apk_filepath: name of the apk, must be saved in base_apk dir
    :param decompiled_apk_filepath: path where decompiled apk needs to be stored
    :return: decompiled apk filepath
    """
    logger.info(f"Decompiling apk {apk_filepath} file")

    if not os.path.isfile(apk_filepath):
        logger.error(f"{apk_filepath} does not exist directory, please add it and try again.")
        raise FileNotFoundError(f"{apk_filepath} does not exist in")

    # test command -- apktool d -f --only-main-classes -o test_123 test124.apk
    command = ["java", "-jar", APKTOOL_FILE, "d", apk_filepath, "-o", decompiled_apk_filepath, "-f"]
    logger.debug(f"command for decompiling apk is {command}")

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error while decompiling apk: {apk_filepath}, exception is {e}")
        raise subprocess.CalledProcessError

    logger.info(f"Successfully decompiled {apk_filepath} to {decompiled_apk_filepath}")
    return decompiled_apk_filepath


def change_package_name(decompiled_apk_filepath: str, new_package_name: str,
                        manifest_filename: str = "AndroidManifest.xml") -> str:
    """
    Change the package name of root element in manifest file.

    :param decompiled_apk_filepath: decompiled apk folder
    :param new_package_name: updated package name
    :param manifest_filename: optional, name of manifest file
    :return: manifest file path
    """
    manifest_filepath = os.path.join(decompiled_apk_filepath, manifest_filename)
    if not os.path.isfile(manifest_filepath):
        logger.error(f"Unable to find manifest file: {manifest_filepath}")
        raise FileNotFoundError(f"Unable to find manifest file: {manifest_filepath}")

    logger.info(f"changing package name")
    logger.debug(f"changing package name from {manifest_filename} path")
    tree = ElementTree.parse(manifest_filepath)
    old_package_name = tree.getroot().get("package")
    tree.getroot().set("package", new_package_name)
    tree.write(manifest_filepath, xml_declaration=True, encoding="utf-8")
    logger.info(f"Changed package name from {old_package_name} to {new_package_name}")
    return manifest_filepath


def compile_apk(decompiled_apk_filepath: str, package_dir: str) -> str:
    """
    compile an apk package
    :param decompiled_apk_filepath: apk filepath
    :return: compiled apk filepath
    """
    apk_name = os.path.split(decompiled_apk_filepath)[-1].split(".")[0] + "_new.apk"
    logger.info(f"Compiling {apk_name} from {decompiled_apk_filepath}")
    output_apk_filepath = os.path.join(package_dir, apk_name)
    zip_align_apk = os.path.join(package_dir, "zip_"+apk_name)
    compile_command = ["java", "-jar", APKTOOL_FILE, "b",  "-f", "--use-aapt2", "-o", output_apk_filepath, decompiled_apk_filepath]
    zip_align_command = [ZIP_ALIGN_FILE, "-p", "4", output_apk_filepath, zip_align_apk]
    sign_apk_command = ["java", "-jar", APK_SIGNER, "sign", "--key", os.path.join(APKTOOL_PATH, "apkeasytool.pk8"),
                        "--cert", os.path.join(APKTOOL_PATH, "apkeasytool.pem"), "-v4-signing-enabled", "false",
                        "--out", output_apk_filepath, zip_align_apk]
    logger.debug(f"command for compiling apk is {compile_command}")
    try:
        subprocess.run(compile_command, check=True)
        subprocess.run(zip_align_command, check=True)
        subprocess.run(sign_apk_command, check=True)
        os.remove(zip_align_apk)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error while compiling {apk_name}, exception is {e}")
        raise subprocess.CalledProcessError
    logger.info(f"Successfully compiled {apk_name} and saved to {output_apk_filepath}")
    return output_apk_filepath
