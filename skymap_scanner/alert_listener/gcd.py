import logging
from pathlib import Path

class GCDManager:
    def __init__(self, gcd_path: str) -> None:
        self.logger = logging.getLogger(__name__)
        self.path = Path(gcd_path)
        self.index = self.build_gcd_index()
        self.runs = sorted(self.index.keys())

    def build_gcd_index(self) -> dict:
        index = dict()
        for path in self.path.glob("*.i3"):

            name = path.stem  # get the filename without the extension

            if "Run" in name:
                # format 'YYYY_MM_DD_RunNNNNNN(.i3)'
                run = int(name.split("_")[3][3:])
            elif "baseline" in name:
                # format 'baseline_gcd_NNNNNN(.i3)'
                run = int(name.split("_")[2])
            else:
                self.logger.warning(
                    f"GCD file name does not match expected format: {name}"
                )

            index[run] = path

        self.logger.info(f"Indexed {len(index)} GCD files in source directory")
        return index

    def get_gcd_path(self, run: int) -> Path:
        gcd_run = self.runs[0]
        for r in self.runs:
            if run >= r:
                gcd_run = r
            else:
                break
        self.logger.debug(
            f"Selecting run {gcd_run} as GCD source for run {run} from {self.runs}"
        )
        return self.index[gcd_run]

    # def get_latest_gcd(self, run):
