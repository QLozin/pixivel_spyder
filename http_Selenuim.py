from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from pathlib import Path


class Selenium(object):
    def __init__(self,driver_path: str = "./Driver/geckodriver.exe", headless: bool = True):
        self.FF_driver = Path(driver_path)
        self.custom_options = Options()
        self.custom_options.headless = headless
    def __enter__(self):
        self.browser = webdriver.Firefox(executable_path=str(self.FF_driver.absolute()), options=self.custom_options)
        return self.browser

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.browser.quit()
        return True
    @staticmethod
    def want_cookies(_browser:webdriver,target_url:str="https://pixivel.moe/"):
        _browser.get(target_url)
        return _browser.get_cookies()

if __name__ == '__main__':
    with Selenium(headless=False) as browser:
        browser.get("https://pixivel.moe/")
        print(browser.get_cookies())