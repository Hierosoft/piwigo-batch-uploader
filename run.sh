#!/bin/bash
cd "$(dirname "$0")" || exit 1
if [ ! -d morepiwigo ]; then
    &>2 echo "Error: Missing 'morepiwigo' in '`pwd`'"
    exit 2
fi
CSV_PATH=your_data.csv
if [ ! -z "$1" ]; then
    CSV_PATH="$1"
fi
python3 run.py --config piwigo-config.json --csv "$CSV_PATH"
# Or override:
# --privacy-level friends
# --share-with-group "othergroup"
