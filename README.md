# Budget-Script

## Purpose
This is a script to scrape and download financial data from linked accounts, process the downloaded data, and generate a budget report

## Requirements
- Python 3.14+
- macOS (automatic MFA bypass)

**NOTE:** If the script is not running on macOS [automatic OTP bypass](#mfa-bypass) cannot be used, refer [here](#skipping-the-mfa-bypass) for steps to proceed without it.

## Setup
### Core Setup (Required)
1. Create the instructions folder with the below files:
    - accounts.json
        - JSON file containing each financial account
        - Details steps to download/scrape data for each account
    - csv_management.json
        - JSON file containing each type of downloaded csv report
        - Details steps to process the downloaded csv for combined financial report
2. Download requirements for the project
    1. Create a python venv
    2. Run ```pip install .```

### launchd Job Setup (Optional)
1. (If running as job else skip to step 4) Create the job folder with the below files:
    - run_script.sh
        - bash script to be run by the job
    - com.name.script-name.plist
        - plist for configuring launchd job
2. Run ```./load_plist.sh <plist>```

### Example Files
There are examples files under **examples/**

**Files:**
- examples/instructions/accounts.json
    - Contains example scraping script for an American Express account
    - A detailed explanation on supported scraping actions can be found [here](#scraping-actions)
- examples/instructions/csv_management.json
    - Contains example cleaning script for a downloaded csv file from an American Express account
    - A detailed explanation on supported actions can be found [here](#csv-management-actions)
- examples/job/run_script.sh
    - An example bash script to clean job related logs and run the python script
- examples/job/com.name.script-name.plist
    - An example plist to configure a launchd job

## Running
Two methods:
- launchd job
    - Automated job that runs at the beginning of each month (previous month's data)
    - Can be run on command using ```launchctl kickstart -k gui/$(id -u)/<com.name.script-name>```
    - **NOTE:** This *requires* automatic MFA bypass as launchd jobs are non-interactive, so you must give the [python executable full disk access](#granting-full-disk-access)
- On-demand from terminal (```python main.py {params}```)
    - Parameters
        - *-d {date_param}*: specify either {end date} or a {start end} date range for scraping
            - Dates must be provided in yyyy-mm-dd format
            - NOTE: when only end date is specified the start date defaults to beginning of the month
        - *--no-scrape*: skips the scraping portion and just runs data cleaning/report generation (useful if re-running a date)
        - *-v, -vv*: increase verbosity for logging
        - *-p*: generates pretty CLI report using the [rich](https://github.com/textualize/rich) library
    - **NOTE:** If using automatic MFA bypass, user must give [full disk access to terminal](#granting-full-disk-access)

## Additional Information
### MFA Bypass
The bypass for MFA is done by selecting the text option for a One-Time Password and then scraping through recent messages to look for this password.

This requires that the user in the apple ecosystem for both their computer and phone with iMessage sharing enabled between them

Due to macOS protections on the chat database, the script *requires* [full disk access](#granting-full-disk-access), if you are not comfortable with that refer [here]()

#### **Granting Full Disk Access**
There are two areas that you will need to grant full disk access depending on how the script is being run

- Running through the terminal
    - System Settings -> Privacy & Security -> Full Disk Access -> Allow for Terminal
- Running through a job
    - System Settings -> Privacy & Security -> Full Disk Access -> Click the + -> Select the python executable
    - If you are using a conda env you may not be able to grant it full disk access, so follow this workaround
        1. Create directory for new executable: ```mkdir /path/to/new_dir```
        2. Copy the conda env executable into this folder: ```cp /path/to/conda/envs/<env_name>/bin/python /path/to/new_dir```
        3. Make this executable: ```chmod +x /path/to/new_dir/python```
        4. Grant this executable full disk access

#### **Skipping the MFA Bypass**
The MFA bypass can be skipped by adding *bypass_poller=True* to the instantiation of the **MessageHandler** class

This instantiation can be found on line 22 of __*scraper.py*__. No other changes are required to skip the MFA bypass. This will lead to a CLI prompt being displayed when MFA is encountered for the user to input the code

**NOTE:** Skipping the automated MFA bypass makes it so that the script can not be run through the automated launchd job, as they can not take user input

### Scraping Actions

| Action Name | Required Keys | Optional Keys | Return Value | Notes |
| :--- | :--- | :--- | :--- | --- |
| navigate | base_url | endpoint, format | None | Using {START} and {END} will be replaced with the corresponding start and end date of the script (can be formatted using the format key) |
| type | selector, value | format | None | supports the following special typing: <ul><li>temp, will be replaced by the return value of the previous step if exists</li> <li>{START} and {END}, will be replaced with the corresponding start and end date of the script (can be formatted using the format key)</li></ul> |
| click | selector | - | None | if the selector is "temp" it will be replaced by the return value of the previous step |
| find_by_xpath | selector | - | Found Element | - |
| wait_for_element | selector | timeout | None | if the selector is "temp" it will be replaced by the return value of the previous step |
| if_is_element | selector, actions | else_fail, duration, poll_interval | None | duration and poll_interval are mutually required |
| wait_for_mfa | duration | poll_interval, regex_pattern, temp_bypass | One-Time Password | using temp_bypass = True will prompt the user via CLI to input the OTP |
| sleep | duration | - | None | - |


### CSV Management Actions

TODO: fill out this section