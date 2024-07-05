import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from aws_appstore_ui import UiAppstoreMainWindow
import multiprocessing

from main import run
from utils import get_running_status, update_running_status, STATUS_FILEPATH


class MainWindow(QMainWindow):
    def __init__(self):
        # self.running = get_running_status()
        self.process = None
        super().__init__()
        self.ui = UiAppstoreMainWindow()
        self.ui.setupUi(self)

        self.ui.start_button.clicked.connect(self.start_button_clicked)
        self.ui.stop_button.clicked.connect(self.stop_button_clicked)

    def start_button_clicked(self):
        if not self.validate_inputs():
            return

        if get_running_status() == "running":
            QMessageBox.warning(self, "Running", "A process is already running. Please stop and try again.")
            return

        self.start_new_process(run, use_local_apk=self.ui.use_local_apk_checkbox.isChecked(),
                               change_package_name=self.ui.change_pkg_yes_checkbox.isChecked(),
                               drm_status=self.ui.drm_yes_checkbox.isChecked(),
                               start_from=self.ui.row_start_from.text())

    def stop_button_clicked(self):
        if get_running_status() == "stopped":
            QMessageBox.warning(self, "Running Status", "No Active Process is running.")
        self.process.terminate()
        self.process.join()
        update_running_status("stopped")
        print("Stop process: ", self.process)

    def validate_inputs(self):
        if self.ui.use_local_apk_checkbox.isChecked() and self.ui.download_apk_checkbox.isChecked():
            QMessageBox.critical(self, "Download Method Error", "Only one option is allowed for download method")
            return False
        elif not self.ui.use_local_apk_checkbox.isChecked() and not self.ui.download_apk_checkbox.isChecked():
            QMessageBox.critical(self, "Download Method Error", "You haven't selected any of the download method. "
                                                                "Please select any one of the download method")
            return False
        elif self.ui.change_pkg_yes_checkbox.isChecked() and self.ui.change_pkg_no_checkbox.isChecked():
            QMessageBox.critical(self, "APK Modification Error", "Only select one apk modification method or keep "
                                                                 "both unchecked.")
            return False
        elif self.ui.drm_yes_checkbox.isChecked() and self.ui.drm_no_checkbox.isChecked():
            QMessageBox.critical(self, "DRM Input Error", "Either Yes or No, only one of the drm input is allowed. ")
            return False
        elif not self.ui.drm_yes_checkbox.isChecked() and not self.ui.drm_no_checkbox.isChecked():
            QMessageBox.critical(self, "DRM Input Error", "You haven't selected any of the DRM option, please select "
                                                          "one of the option")
            return False
        elif self.ui.row_start_from.text():
            try:
                int(self.ui.row_start_from.text())
                return True
            except ValueError:
                QMessageBox.critical(self, "Invalid start row", "Please enter an valid integer")
                return False
        else:
            return True

    def start_new_process(self, func, *args, **kwargs):
        proc = multiprocessing.Process(target=func, args=args, kwargs=kwargs)
        # proc = Thread(target=func, args=args, kwargs=kwargs)
        proc.start()
        update_running_status("running")
        self.process = proc


if __name__ == "__main__":
    with open(STATUS_FILEPATH, 'w', encoding="utf-8") as fp:
        fp.write("stopped")

    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())
