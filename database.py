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
        df = pd.DataFrame.from_dict(records_data)
        print(df.head())

        projSheet = self.shClient.open("dlmastersheet").get_worksheet(1)
        proj_data = projSheet.get_all_records()
        self.dProj = pd.DataFrame.from_dict(proj_data)

    def get_all_pods(self):
        df = pd.DataFrame(self.sheet.get_all_records())
        return list(set(df["pod"]))

    def get_all_megapods(self):
        df = pd.DataFrame(self.sheet.get_all_records())
        return list(set(df["megapod"]))

    def get_student_by_email(self, email):
        df = pd.DataFrame.from_dict(self.sheet.get_all_records())
        cellInfo = df[df["email"] == email].index.values[0]
        return {
            "name": df.at[cellInfo, "name"],
            "pod": df.at[cellInfo, "pod"],
            "role": df.at[cellInfo, "role"],
            "email": email,
            "megapod": df.at[cellInfo, "megapod"],
            "timezone": df.at[cellInfo, "timezone"],
        }

    def get_student_by_discord_id(self, discord_id):
        df = pd.DataFrame.from_dict(self.sheet.get_all_records())
        if discord_id not in df["discord id"].tolist():
            return {}
        else:
            cellInfo = df[df["discord id"] == discord_id].index.values[0]
            return {
                "name": df.at[cellInfo, "name"],
                "pod": df.at[cellInfo, "pod"],
                "role": df.at[cellInfo, "role"],
                "email": df.at[cellInfo, "email"],
                "megapod": df.at[cellInfo, "megapod"],
                "timezone": df.at[cellInfo, "timezone"],
            }

    def get_megapod_for_pod(self, pod):
        df = pd.DataFrame(self.sheet.get_all_records())
        return df.at[df[df["pod"] == pod].index.values[0], "megapod"]

    def get_timezone_for_pod(self, pod):
        df = pd.DataFrame.from_dict(self.sheet.get_all_records())
        return df.at[df[df["pod"] == pod].index.values[0], "timezone"]

    def set_students_discord_ids(self, names_to_ids):
        df = pd.DataFrame.from_dict(self.sheet.get_all_records())
        for name, discord_id in names_to_ids.items():
            if name in df["name"].to_list():
                cellInfo = df[df["name"] == name].index.values[0]
                df.at[cellInfo, "discord id"] = f"{discord_id}_"

        self.sheet.update([df.columns.values.tolist()] + df.values.tolist())

    def set_student_discord_id(self, email, discord_id):
        df = pd.DataFrame.from_dict(self.sheet.get_all_records())
        cellInfo = df[df["email"] == email].index.values[0]
        self.sheet.update_cell(int(cellInfo + 2), 7, f"{discord_id}_")
