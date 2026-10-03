import logging
import sys

from app.logs import setup_logging
from app.products import load_tracked, product_url, read_raw_history
from app.scraper import save_data
from app.scraper.load_data import ExtractData
from app.scraper.process_data import ProcessData

log = logging.getLogger(__name__)


def main() -> None:
    """Scrape every tracked product once and save the prices to the CSV."""
    log.info("Scrape started")

    extract_data = ExtractData(gpu_list=[product_url(a) for a in load_tracked()])

    raw_data = extract_data.bs_extraction()

    # Raw, uncleaned, so new rows append in the stored format
    historical_data = read_raw_history()

    processed_data = ProcessData(
        raw_data=raw_data["gpu_raw_data"],
        url_list=raw_data["url_list"],
        historical_data=historical_data,
    )

    processed_data.create_gpu_df()

    gpu_data = processed_data.concat_historical_data()

    save_data.write_csv(df=gpu_data)

    log.info("Saved %d history rows", len(gpu_data))


if __name__ == "__main__":
    setup_logging()
    try:
        main()
    except Exception:
        log.exception("Scrape failed")
        sys.exit(1)
