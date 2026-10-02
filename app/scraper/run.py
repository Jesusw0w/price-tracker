from app.products import load_tracked, product_url
from app.scraper import save_data
from app.scraper.load_data import ExtractData
from app.scraper.process_data import ProcessData


def main() -> None:
    print("App Starting...", flush=True)

    extract_data = ExtractData(gpu_list=[product_url(a) for a in load_tracked()])

    raw_data = extract_data.bs_extraction()

    historical_data = extract_data.load_historical_data()

    processed_data = ProcessData(
        raw_data=raw_data["gpu_raw_data"],
        url_list=raw_data["url_list"],
        historical_data=historical_data,
    )

    processed_data.create_gpu_df()

    gpu_data = processed_data.concat_historical_data()

    save_data.write_csv(df=gpu_data)

    print("Data Saved", flush=True)


if __name__ == "__main__":
    main()
