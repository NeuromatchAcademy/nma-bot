from oauth2client.service_account import ServiceAccountCredentials
import gspread
import pandas as pd


class GSheetDb:
    def __init__(self):
        pass

    def connect(self):
        gAuthJson = "sound-country-274503-cd99a71b16ae.json"
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(gAuthJson, scope)

        self.shClient = gspread.authorize(creds)
        self.sheet = self.shClient.open("dlmastersheet").sheet1
        records_data = self.sheet.get_all_records()
        self.df = pd.DataFrame.from_dict(records_data)
        print(self.df.head())

        projSheet = self.shClient.open("dlmastersheet").get_worksheet(1)
        proj_data = projSheet.get_all_records()
        self.dProj = pd.DataFrame.from_dict(proj_data)

    def get_all_pods(self):
        df = pd.DataFrame(self.sheet.get_all_records())
        return list(set(df["pod"]))

    def get_all_megapods(self):
        df = pd.DataFrame(self.sheet.get_all_records())
        return list(set(df["megapod"]))

    def get_megapod_for_pod(self, pod):
        df = pd.DataFrame(self.sheet.get_all_records())
        return df.at[df[df["pod"] == pod].index.values[0], "megapod"]
