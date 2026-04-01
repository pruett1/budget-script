#!/bin/bash

# load conda env
PYTHON=/path/to/conda/envs/<your_conda_env>/bin/python
# If for full disk access need to copy python exec then use path to that

# navigate to dir
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.."
cd $DIR
# cd /Users/oliverpruett/Desktop/Code/git/budget-script

if [ -f "$DIR/job/launchd.out.log" ]; then
    rm "$DIR/job/launchd.out.log"
fi

if [ -f "$DIR/job/launchd.err.log" ]; then
    rm "$DIR/job/launchd.err.log"
fi

#set end_date
END_DATE=$(date -v-1d +"%Y-%m-%d")

# run the script
$PYTHON main.py  -p -vv --date "$END_DATE"