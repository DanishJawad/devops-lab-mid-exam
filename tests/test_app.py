import os
import uuid

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

APP_URL = os.environ.get("APP_URL", "http://localhost")


@pytest.fixture
def driver():
    options = webdriver.ChromeOptions()
    if os.environ.get("HEADLESS") == "1":
        options.add_argument("--headless=new")
    d = webdriver.Chrome(options=options)  # Selenium Manager fetches the driver
    yield d
    d.quit()


def test_page_loads_and_shows_title(driver):
    driver.get(APP_URL)
    assert driver.title == "Lab Notes"
    heading = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "app-title"))
    )
    assert heading.text == "Lab Notes"
    assert driver.find_element(By.ID, "served-by").text.strip() != ""


def test_add_note_appears_in_list(driver):
    # Behind the load balancer this needs sticky sessions on the target group:
    # each instance has its own database, so the POST and the redirected GET
    # must reach the same instance.
    text = f"selenium-{uuid.uuid4().hex[:8]}"
    driver.get(APP_URL)
    driver.find_element(By.ID, "note-body").send_keys(text)
    driver.find_element(By.ID, "note-submit").click()
    WebDriverWait(driver, 10).until(
        EC.text_to_be_present_in_element((By.ID, "notes-list"), text)
    )
