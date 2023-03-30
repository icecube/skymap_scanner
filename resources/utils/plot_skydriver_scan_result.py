"""A helper script to make a plot from SkyDriver's serialized result format."""

import argparse

from rest_tools.client import RestClient
from skymap_scanner.utils.scan_result import SkyScanResult

parser = argparse.ArgumentParser(description="Make plot of scan result from SkyDriver")
parser.add_argument("--token", help="skydriver token", required=True)
parser.add_argument("--scan-id", help="skydriver scan id", required=True)
args = parser.parse_args()

rc = RestClient("https://skydriver.icecube.aq", token=args.token, retries=0)
serialzed = rc.request_seq("GET", f"/scan/result/{args.scan_id}")["skyscan_result"]

result = SkyScanResult.deserialize(serialzed)
result.create_plot(dosave=True)
result.create_plot_zoomed(dosave=True)
