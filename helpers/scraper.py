from seleniumbase import SB
from selenium.webdriver.common.by import By
import os

from datetime import datetime
import logging

import json
import time

from helpers.messages import MessageHandler

class Scraper:
    def __init__(self, end_date: datetime, report_dir: str, logger: logging.Logger, start_date: datetime|None = None):
        self.logger = logger
        self.logger.debug("Initialized Scraper")  # Log initialization

        self.end_date = end_date
        self.start_date = start_date if start_date else end_date.replace(day=1)
        self.report_dir = report_dir

        self.message_handler = MessageHandler(self.logger)

        with open("instructions/accounts.json", "r") as f:
            self.accounts = json.load(f)

    def set_sb(self, sb: SB):
        self.sb = sb

    def get_target_account(self, account_name): # this mostly just used for testing purposes
        target = None
        for account in self.accounts["accounts"]:
            if account["name"] == account_name:
                target = account
                break

        if target is None:
            raise ValueError(f"Account with name {account_name} not found in instructions/accounts.json")
        
        return target
    
    def take_action(self, action_obj: dict, temp = None):
        assert "action" in action_obj, "Action object must have an 'action' key"

        # Allowed actions:
        # - "navigate": required "base_url" key and optional "endpoint" and "format" keys, returns None
        # - "type": required "selector" and "value" keys, optional "format" key, returns None
        # - "click": required "selector" key, returns None
        # - "find_by_xpath": required "selector" key, returns the found element
        # - "wait_for_mfa": required "duration" key, optional "poll_interval", "regex_pattern" and "temp_bypass" keys, returns OTP
        # - "wait_for_element": required "selector" key, optional "timeout" key, returns None
        # - "if_is_element": required "selector" and "actions" key, optional "else_fail" key, returns None
        #   - optional keys for polling "duration" and "poll_interval" are mutually required
        # - "sleep": required "duration" key, returns None

        # if there is a "temp" placeholder in action object replace it with temp parameter
        for k, v in action_obj.items():
            if isinstance(v, str) and v == "temp":
                action_obj[k] = temp

        action = action_obj["action"]
        self.logger.debug(f"Performing action: {action} with parameters: {action_obj}")
        match action:
            case "navigate":
                return self.navigate(action_obj)
            case "type":
                return self.type(action_obj)
            case "click":
                return self.click(action_obj)
            case "find_by_xpath":
                self.assert_required_keys(action_obj, ["selector"])
                return self.sb.find_element(By.XPATH, action_obj["selector"])
            case "wait_for_mfa":
                return self.wait_for_mfa(action_obj)
            case "wait_for_element":
                self.assert_required_keys(action_obj, ["selector"])
                self.sb.wait_for_element(action_obj["selector"], timeout=action_obj.get("timeout", 10))
                return None
            case "if_is_element":
                return self.if_is_element(action_obj)
            case "sleep":
                self.assert_required_keys(action_obj, ["duration"])
                time.sleep(action_obj["duration"])
            case _:
                raise ValueError(f"Unsupported action: {action}")
            
    def assert_required_keys(self, action_obj, required_keys):
        for key in required_keys:
            if key not in action_obj:
                self.logger.error(f"Missing required key ({key}) in {action_obj}")
                raise ValueError()
            
    def navigate(self, action_obj):
        self.assert_required_keys(action_obj, ["base_url"])
        base = action_obj["base_url"]
        endpoint = action_obj.get("endpoint")
        if endpoint:
            fmt = action_obj.get("format", "%Y-%m-%d")
            endpoint = endpoint.replace("{START}", self.start_date.strftime(fmt))
            endpoint = endpoint.replace("{END}", self.end_date.strftime(fmt))
        else:
            endpoint = ""

        self.logger.debug(f"Navigating to: {base + endpoint}")

        url = base + endpoint
        self.sb.open(url)
        return None
    
    def type(self, action_obj):
        self.assert_required_keys(action_obj, ["selector", "value"])
        value = action_obj["value"]
        if "{START}" in value or "{END}" in value:
            fmt = action_obj.get("format", "%Y-%m-%d")
            value = value.replace("{START}", self.start_date.strftime(fmt))
            value = value.replace("{END}", self.end_date.strftime(fmt))

        self.sb.type(action_obj["selector"], value)
        return None
    
    def click(self, action_obj):
        self.assert_required_keys(action_obj, ["selector"])
        if not isinstance(action_obj["selector"], str): 
            action_obj["selector"].click()
            return None
        self.sb.click(action_obj["selector"])
        return None
    
    def wait_for_mfa(self, action_obj):
        self.assert_required_keys(action_obj, ["duration"])
        duration = action_obj["duration"]
        poll_interval = action_obj.get("poll_interval", 1) # default to 1 second poll interval
        regex_pattern = action_obj.get("regex_pattern", r"\b\d{6}\b")  # default to 6 digit code
        temp_bypass = action_obj.get("temp_bypass", False)

        return self.message_handler.poll_for_otp(duration=duration, 
                                                 poll_interval=poll_interval, 
                                                 regex_pattern=regex_pattern, 
                                                 temp_bypass=temp_bypass)
    
    def if_is_element(self, action_obj):
        self.assert_required_keys(action_obj, ["selector", "actions"])
        if "duration" in action_obj:
            self.assert_required_keys(action_obj, ["duration", "poll_interval"])

        selector = action_obj["selector"]
        fail_if_else = action_obj.get("fail_if_else", False)
        actions_performed = False

        duration = action_obj.get("duration", 1)
        poll_interval = action_obj.get("poll_interval", 1)
        start = time.time()

        while time.time() - start < duration:
            if self.sb.is_element_present(selector):
                self.perform_actions(action_obj["actions"])
                actions_performed = True
                break
            time.sleep(poll_interval)

        if fail_if_else and not actions_performed:
            self.logger.error(f"Element {selector} is not present and fail_if_else True")
            raise ValueError()
        
        return None

    def perform_actions(self, actions: list[dict]):
        temp = None
        for action in actions:
            temp = self.take_action(action, temp=temp)
            if temp is not None:
                self.logger.debug(f"Action returned value: {temp}")

    def manage_downloads(self, download_dir: str, target: dict):
        os.path.join(os.getcwd(), download_dir)

        for filename in os.listdir(download_dir):
            if filename.endswith(".csv"):
                src = os.path.join(download_dir, filename)
                new_filename = f"{target['name']}_{target['type']}.csv"

                dst = os.path.join(os.getcwd(), self.report_dir, new_filename)

                if os.path.exists(dst):
                    self.logger.warning(f"File {dst} already exists. It will be overwritten.")
                    os.remove(dst)

                os.rename(src, dst)
                self.logger.debug(f"Moved downloaded file from {src} to {dst}")

    def run(self):
        for account in self.accounts["accounts"]:
            self.logger.info(f"Processing account: {account['name']} of type {account['type']}")
            self.perform_actions(account["scraping_actions"])
            time.sleep(5) # allow time for download
            self.manage_downloads("downloaded_files", account)

        self.logger.info("Finished processing all accounts")
