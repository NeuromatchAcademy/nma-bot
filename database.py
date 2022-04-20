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

        projSheet = self.shClient.open("dlmastersheet").get_worksheet(1)
        proj_data = projSheet.get_all_records()
        self.dProj = pd.DataFrame.from_dict(proj_data)
