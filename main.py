from helpers.scraper import Scraper
from helpers.csv_mgmt import CSVManager
from helpers.report import ReportManager

from seleniumbase import SB
import os
from datetime import datetime

import logging
import argparse

def parse_date(date_str: str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except:
        raise ValueError("Invalid date format: must be YYYY-MM-DD")

def handle_date_arg(args):
    end_date = datetime.now()
    start_date = None
    if args.date:
        if len(args.date) == 1:
            end_date = parse_date(args.date[0])
        elif len(args.date) == 2:
            start_date = parse_date(args.date[0])
            end_date = parse_date(args.date[1])
            if start_date == end_date:
                raise ValueError("Must provide valid range (minimum of 1 day)")

            if start_date > end_date:
                start_date, end_date = end_date, start_date
        else:
            raise ValueError("Incorrect amount of dates provided")
    
    return start_date, end_date

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-scrape', action="store_true", help="Skips the web scraping and just handles downloaded CSV files")
    parser.add_argument('-d', '--date', nargs="+", help="Provide one date (end) or two dates (start end) in YYYY-MM-DD format (default start date is beginning of month)")
    parser.add_argument('-v', '--verbose', action="count", default=0, help="Increase verbosity (-v, -vv): \n-v includes INFO logs and more detailed spending category breakdown, \n-vv includes all debug logs")
    parser.add_argument('-p', '--pretty-report', action="store_true", help="Generate more than just an HTML report")

    levels = {
        0: logging.ERROR,
        1: logging.INFO,
        3: logging.DEBUG
    }

    args = parser.parse_args()

    level = levels.get(args.verbose, logging.DEBUG)
    logging.basicConfig(level=level)

    logger = logging.getLogger("main")
    logger.debug("Starting main script")

    start_date, end_date = handle_date_arg(args)

    report_dir = "reports/monthly_budget_report_" + end_date.strftime("%Y-%m-%d")
    if start_date:
        report_dir = "reports/monthly_budget_report_" + start_date.strftime("%Y-%m-%d") + "_" + end_date.strftime("%Y-%m-%d")
    
    os.makedirs(report_dir, exist_ok=True)

    if not args.no_scrape:
        scraper = Scraper(end_date, report_dir, logger, start_date=start_date)

        with SB(uc=True) as sb:
            scraper.set_sb(sb)
            scraper.run()

    csv_manager = CSVManager(report_dir, logger)

    csv_manager.load_csvs()
    csv_manager.clean_all_csvs()
    combined = csv_manager.get_combined_finances()

    report_manager = ReportManager(args, logger)
    if args.pretty_report:
        report_manager.generate_pretty_cli_report(combined)
    else:
        report_manager.generate_cli_report(combined)