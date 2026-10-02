"""Highlight every row whose status is Failed in red.

Usage: python -m scripts.mark_red
"""
from mailer import config, tracker

if __name__ == "__main__":
    tracker.mark_failed_rows_red(config.SHEET_PATH, config.STATUS_COL_INDEX)
