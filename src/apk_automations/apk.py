import subprocess
import sys
from pathlib import Path
import os
from xml.etree import ElementTree

sys.path.append("..")

from logger import logger

SRC_DIR = Path(__file__).resolve().parents[1]
APKTOOL_FILE = os.path.join(SRC_DIR, 'apk_automations', "apktools", "apktool.bat")
APK_SIGNER = os.path.join(SRC_DIR, 'apk_automations', "apktools", "apksigner.jar")
APKTOOL_PATH = os.path.join(SRC_DIR, 'apk_automations', "apktools")
INPUT_APK_DIR = os.path.join(SRC_DIR, "base_apk")
TEMP_OUTPUT_DIR = os.path.join(INPUT_APK_DIR, "temp")

if not os.path.exists(TEMP_OUTPUT_DIR):
    os.mkdir(TEMP_OUTPUT_DIR)


def decompile_apk(apk_file_name: str) -> str:
    """
    Decompile an apk
    :param apk_file_name: name of the apk, must be saved in base_apk dir
    :return: decompiled apk filepath
    """
    apk_filepath = os.path.join(INPUT_APK_DIR, apk_file_name)
    logger.info(f"Decompiling apk {apk_filepath} file")

    if not os.path.isfile(apk_filepath):
        logger.error(f"{apk_filepath} does not exist in {INPUT_APK_DIR} directory, please add it and try again.")
        raise FileNotFoundError(f"{apk_filepath} does not exist in")

    decompiled_apk_filepath = os.path.join(TEMP_OUTPUT_DIR, apk_file_name.split(".")[0])
    # test command -- apktool d -f --only-main-classes -o test_123 test124.apk
    command = [APKTOOL_FILE, "d", apk_filepath, "-o", decompiled_apk_filepath, "-f"]
    logger.debug(f"command for decompiling apk is {command}")

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error while decompiling apk: {apk_file_name}, exception is {e}")
        raise subprocess.CalledProcessError

    logger.info(f"Successfully decompiled {apk_file_name} to {decompiled_apk_filepath}")
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
    logger.info(f"changing package name")
    logger.debug(f"changing package name from {manifest_filename} path")
    tree = ElementTree.parse(manifest_filepath)
    old_package_name = tree.getroot().get("package")
    tree.getroot().set("package", new_package_name)
    tree.write(manifest_filepath, xml_declaration=True, encoding="utf-8")
    logger.info(f"Changed package name from {old_package_name} to {new_package_name}")
    return manifest_filepath


def compile_apk(decompiled_apk_filepath: str) -> str:
    """
    compile an apk package
    :param decompiled_apk_filepath: apk filepath
    :return: compiled apk filepath
    """
    apk_name = os.path.split(decompiled_apk_filepath)[-1].split(".")[0] + ".apk"
    logger.info(f"Compiling {apk_name} from {decompiled_apk_filepath}")
    output_apk_filepath = os.path.join(TEMP_OUTPUT_DIR, apk_name)
    compile_command = [APKTOOL_FILE, "b",  "-f", "--use-aapt2", "-o", output_apk_filepath, decompiled_apk_filepath]
    sign_apk_command = ["java", "-jar", APK_SIGNER, "sign", "--key", os.path.join(APKTOOL_PATH, "apkeasytool.pk8"), "--cert",
                        os.path.join(APKTOOL_PATH, "apkeasytool.pem"), "-v4-signing-enabled", "false", "--out",
                        output_apk_filepath, output_apk_filepath]
    logger.debug(f"command for compiling apk is {compile_command}")
    try:
        subprocess.run(compile_command, check=True)
        subprocess.run(sign_apk_command, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error while compiling {apk_name}, exception is {e}")
        raise subprocess.CalledProcessError
    logger.info(f"Successfully compiled {apk_name} and saved to {output_apk_filepath}")
    return output_apk_filepath
