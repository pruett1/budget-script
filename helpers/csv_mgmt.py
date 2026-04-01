import pandas as pd
import os
import json
import numpy as np

import logging
import json
import operator

class CSVManager:
    def __init__(self, dir_path: str, logger: logging.Logger):
        self.logger = logger
        self.dir_path = dir_path

        with open("instructions/csv_management.json", "r") as f:
            self.csv_mgmt = json.load(f)

        self.op_map = {
            ">": operator.gt,
            ">=": operator.ge,
            "<": operator.lt,
            "<=": operator.le,
            "==": operator.eq,
            "!=": operator.ne,
        }

    def generate_filenames(self):
        filenames = []
        with open("instructions/accounts.json", "r") as f:
            accounts = json.load(f)
            for account in accounts["accounts"]:
                filename = account["name"] + "_" + account["type"]
                filenames.append(filename)

        self.logger.debug(f"Generated all possible csv filenames: {filenames}")
        return filenames
    
    def load_csvs(self):
        self.logger.info(f"Loading CSVs from {self.dir_path}")
        if not os.path.exists(self.dir_path):
            raise ValueError("Invalid Path To Datafiles")
        
        filenames = self.generate_filenames()
        
        dfs = {}
        
        for filename in filenames:
            path_to_file = self.dir_path + "/" + filename + ".csv"
            if os.path.exists(path_to_file):
                temp_df = pd.read_csv(path_to_file)
                temp_df.columns = temp_df.columns.str.lower()
                dfs[filename] = temp_df

                self.logger.debug(f"CSV {filename} loaded")

        self.dfs = dfs

    def filter_csv(self, csv_name: str):
        if csv_name not in self.dfs:
            raise ValueError(f"{csv_name} not in {self.dfs.keys()}")
        
        df = self.dfs[csv_name]
        filter_inst = self.csv_mgmt[csv_name]["filter"]

        method = filter_inst["method"]
        logic = filter_inst["logic"]
        self.logger.debug(f"Filtering {csv_name} by {method} with logic {logic}")

        match method:
            case "operator":
                col = logic["column_name"]
                val = logic["value"]
                mask = self.op_map[logic["operator"]](df[col], val)
                df = df[mask]
            case "value_list":
                col = logic["column_name"]
                exclude_list = logic["exclude_list"]
                drop_mask = ~df[col].str.contains("|".join(exclude_list))
                df = df[drop_mask]
            case _:
                raise ValueError("Unsupported filter method")
        
        self.dfs[csv_name] = df

    def apply_cat_map(self, df: pd.DataFrame, map: dict, mask_col: str, target_col: str, default: str|None = None):
        for k, v in map.items():
            mask = df[mask_col].str.contains(k, case=False, na=False)
            df.loc[mask, target_col] = v

        if default:
            unmatched_mask = ~df[mask_col].str.contains('|'.join(map.keys()), case=False, na=False)
            df.loc[unmatched_mask, target_col] = default

        return df

    def apply_change(self, df: pd.DataFrame, change: pd.DataFrame):
        method = change["method"]
        logic = change["logic"]
        self.logger.debug(f"applying change of method {method} with logic {logic}")

        # supported methods:
        # column_rename: 

        match method:
            case "column_rename":
                df.rename(columns={logic["target_col"]: logic["new_name"]}, inplace=True)
            case "add_column":
                df[logic["new_col"]] = logic["value"]
            case "map_values":
                mapping_method = logic["mapping_method"]
                if mapping_method == "dict":
                    df = self.apply_cat_map(df, logic["map"], logic["mask_col"], logic["target_col"], logic.get("default"))
                elif mapping_method == "func":
                    fn = eval(logic["map"])
                    target = logic["target_col"]
                    mask = self.op_map[logic["mask_op"]](df[logic["mask_col"]], logic["mask_val"])

                    df.loc[mask, target] = fn(df.loc[mask, target])
                else:
                    raise ValueError(f"Unsupported mapping method {mapping_method}")
                
        return df
                
    def apply_all_changes(self, csv_name: str):
        if csv_name not in self.dfs:
            raise ValueError(f"{csv_name} not in {self.dfs.keys()}")
        
        df = self.dfs[csv_name]
        changes = self.csv_mgmt[csv_name]["changes"]

        self.logger.info(f"Applying {len(changes)} changes to {csv_name}")

        for change in changes:
            df = self.apply_change(df, change)

        self.dfs[csv_name] = df

    def clean_all_csvs(self):
        self.logger.info(f"Cleaning all csvs according to instructions/csv_management.json")
        for name in self.dfs.keys():
            self.logger.debug(f"Cleaning {name}")
            self.filter_csv(name)
            self.apply_all_changes(name)

    def get_common_cols(self):
        if not self.dfs:
            raise ValueError("No CSVs loaded!")

        return list( set.intersection(*(set(df.columns) for df in self.dfs.values())) )
    
    def get_combined_finances(self):
        common_cols = self.get_common_cols()

        return pd.concat([df[common_cols] for df in self.dfs.values()], ignore_index=True)
