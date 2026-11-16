#!/usr/bin/env python3
"""
Launcher for the morepiwigo batch uploader.

Usage (from the piwigo-batch-uploader directory):
  python run.py --config piwigo_config.json --csv data.csv
  python run.py --config piwigo_config.json --csv data.csv --dry-run
  python run.py --config piwigo_config.json --csv data.csv --friends-group Friends

Or after `pip install -e .`:
  piwigo-batch-uploader --config piwigo_config.json --csv data.csv
"""

from morepiwigo.main import main

if __name__ == "__main__":
    main()
