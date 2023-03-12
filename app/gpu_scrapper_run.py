from config import config_obj
from resources.load_data import ExtractData
from resources.process_data import ProcessData
from resources.plots import Plot
from resources import save_data


def main(category: str):
    """
    Amazon Spain Web Scrapper Main file - calls all the resources necessary to display the data
    """
    print("App Starting...", flush=True)

    if category == "":
        category = "all"

    extract_data = ExtractData(gpu_list=config_obj["gpu_links"]["all"], category=category, config=config_obj)

    # Extract amazon gpu webpages HTML for each of the gpu links provided
    raw_data = extract_data.bs_extraction()

    # Extract data stored in a CSV file with all existing historical data
    historical_data = extract_data.load_historical_data()

    processed_data = ProcessData(raw_data=raw_data["gpu_raw_data"], url_list=raw_data["url_list"],
                                 historical_data=historical_data)

    processed_data.create_gpu_df()

    gpu_data = processed_data.concat_historical_data()

    save_data.write_csv(df=gpu_data)

    price_history = Plot(df=gpu_data, x="Date", y="Price", legend="GPU").linear_plot()
    print("Data Saved", flush=True)


if __name__ == "__main__":
    main(category="all")
