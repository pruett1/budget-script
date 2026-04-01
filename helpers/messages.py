import sqlite3
from pathlib import Path
from datetime import datetime, timedelta, timezone
import re
import time
import logging

class MessageHandler:
    def __init__(self, logger: logging.Logger, bypass_poller = False):
        self.logger = logger
        self.bypass_poller = bypass_poller

        if not bypass_poller:
            db_path = Path.home() / "Library/Messages/chat.db"
            self.logger.debug(f"Connecting to Messages DB at: {db_path}")

            self.conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            self.cursor = self.conn.cursor()

        self.apple_epoch = datetime(2001, 1, 1, tzinfo=timezone.utc)
        
        self.otp_ignore_list = set() # keep track of OTPs already used

    def __del__(self):
        try:
            self.logger.debug("Closing DB connection")
            self.conn.close()
        except:
            self.logger.debug("DB connection already closed")
        
    def _parse_messages(self, text, attributed):
        if text:
            return text
        
        if attributed:
            try:
                return attributed.decode("utf-8", errors="ignore")
            except:
                self.logger.error("Error decoding attributed body")
                raise

        self.logger.error("No text or attributed body provided")
        raise ValueError

    def get_messages(self, lookback_time=60):
        self.logger.debug(f"Fetching messages from the last {lookback_time} seconds")
        earliest_time = datetime.now(timezone.utc) - timedelta(seconds=lookback_time)
        earliest_time = int((earliest_time - self.apple_epoch).total_seconds() * 1e9)

        query = "SELECT text, attributedBody, date FROM message WHERE date >= ? ORDER BY date DESC"

        self.cursor.execute(query, (earliest_time,))
        rows = self.cursor.fetchall()
        self.logger.debug(f"Fetched {len(rows)} messages from DB")
        return [self._parse_messages(text, attributed) for text, attributed, _ in rows]
    
    def extract_otp(self, messages, regex_pattern):
        for msg in messages:
            match = re.search(regex_pattern, msg)
            if match:
                otp = match.group(0)
                if otp and otp not in self.otp_ignore_list:
                    return otp
            
        self.logger.debug("No OTP found in messages")
        return None

    def poll_for_otp(self, duration=60, poll_interval=1, regex_pattern=r"\b\d{6}\b", temp_bypass=False):
        if not (self.bypass_poller and temp_bypass):
            self.logger.debug(f"Polling for MFA codes for {duration} seconds...")

            end_time = datetime.now() + timedelta(seconds=duration)
            while datetime.now() < end_time:
                recent = self.get_messages(lookback_time=poll_interval+0.2) # add some overlap bc of time between calls
                otp = self.extract_otp(recent, regex_pattern)
                if otp:
                    self.logger.debug(f"Found OTP: {otp}")
                    self.otp_ignore_list.add(otp)
                    return otp
                
                time.sleep(poll_interval)

            self.logger.debug("Could not find OTP within specified duration")
        else:
            self.logger.debug("Bypassing polling")
        return input("Enter OTP manually: ").strip()