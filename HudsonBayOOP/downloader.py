"""Backward-compatible import for the modular downloader."""

from src.data_download.downloader import DownloadSummary, NSIDCDownloader

__all__ = ["DownloadSummary", "NSIDCDownloader"]
