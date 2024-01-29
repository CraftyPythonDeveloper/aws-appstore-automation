# Amazon App Store Automation

This repo is about automating entire app submission workflow using **Python Selenium** on [amazon app store](https://www.amazon.com/gp/mas/get/amazonapp).
<br><br> This includes below automation modules.
* Automation on apk file and screenshots downloading from Google Play and save it locally.
* Automation on app related long and short description, apk features generation using [google's generative ai](https://ai.google.dev/docs/gemini_api_overview).
* Auto login with 2 factor authentication
* Auto captcha solver
* Auto new app creation and submission
* Multi-user login and app submission supported
* End to end automation, from downloading apk to submitting to app store

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Support](#support)
- [Contributing](#contributing)

## Installation

* Make sure python is installed and accessable through terminal/cmd by typing ```python --version``` or ```python3 --version```
* (Optional step) Create virtual environment by following tutorial on [How to install virtual environment](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/)
* Clone the repo locally using ```git clone https://github.com/CraftyPythonDeveloper/aws-appstore-automation```
* Install requirements ```pip install -r requirements.txt```

## Usage

To run the script follow the below mentioned steps:

- Obtain google's Gemini api key from [here](https://ai.google.dev/docs/gemini_api_overview).
- Update the config.xlsx file, as per the template located inside src directory **config.xlsx**.
- In config sheet add apk related details and in creds add login related details.
- Once config file is updated correctly, you can run the script by typing ```python main.py```

## Support

- If you face any issue or bug, you can create an issue describing the error message and steps to reproduce the same error, with log file attached.

Please [open an issue](https://github.com/CraftyPythonDeveloper/aws-appstore-automation/issues/new) for support.

## Contributing

Please contribute by create a branch, add commits, and [open a pull request](https://github.com/CraftyPythonDeveloper/aws-appstore-automation/pulls).