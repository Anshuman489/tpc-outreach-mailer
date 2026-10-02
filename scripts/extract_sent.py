"""Combine Sent rows from INPUT_SHEETS into OUTPUT_SHEET, de-duplicated by address.

Usage: python -m scripts.extract_sent
"""
from mailer import config, tracker

if __name__ == "__main__":
    tracker.extract_sent(config.INPUT_SHEETS, config.OUTPUT_SHEET)
