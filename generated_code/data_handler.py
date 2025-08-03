import csv
import logging

class DataHandler:
    def __init__(self, data_source):
        self.data_source = data_source

    def get_historical_data(self):
        try:
            with open(self.data_source, "r") as csvfile:
                datareader = csv.DictReader(csvfile)
                return [row for row in datareader]
        except FileNotFoundError:
            logging.error(f"Data source file {self.data_source} not found.")
            raise
        except Exception as e:
            logging.error(f"An error occurred while reading data: {e}")
            raise
