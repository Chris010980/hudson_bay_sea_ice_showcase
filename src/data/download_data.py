"""Command line entry point for raw NSIDC data downloads."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence

from src.data.downloader import DEFAULT_NSIDC_GEOTIFF_URL, NSIDCDownloader
from src.logging_config import configure_logging


logger = logging.getLogger(__name__)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download raw NSIDC GeoTIFF data.")
    parser.add_argument("--base-url", default=DEFAULT_NSIDC_GEOTIFF_URL)
    parser.add_argument("--output-dir", default="data/geotiff")
    parser.add_argument("--product", default="concentration")
    parser.add_argument("--year", action="append", dest="years")
    parser.add_argument("--month", action="append", dest="months")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--log-file")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    configure_logging(level=args.log_level, log_file=args.log_file)

    downloader = NSIDCDownloader(
        base_url=args.base_url,
        local_base=args.output_dir,
        product=args.product,
    )
    summary = downloader.sync(
        years=args.years,
        months=args.months,
        dry_run=args.dry_run,
    )

    logger.info(
        "Download stage complete: "
        "checked=%s, downloaded=%s, skipped=%s, failed=%s",
        summary.checked_files,
        summary.downloaded_files,
        summary.skipped_files,
        summary.failed_files,
    )


if __name__ == "__main__":
    main()
