import pandas as pd
import requests
import sqlite3
import tempfile
from datetime import datetime, timezone

URL = "https://files.russss.dev/nhs_covid19_app_data.db"


class NHSAppData:
    def __init__(self):
        self.dbfile = tempfile.NamedTemporaryFile()
        res = requests.get(URL)
        res.raise_for_status()
        self.dbfile.write(res.content)
        self.conn = sqlite3.connect(self.dbfile.name)
        self.cur = self.conn.cursor()

    def __del__(self):
        self.conn.close()
        self.dbfile.close()

    def exposures(self):
        self.cur.execute(
            "SELECT export_date, rolling_start_interval_number * 600, rolling_period,"
            " transmission_risk_level, report_type, days_since_onset_of_symptoms FROM"
            " exposure_keys"
        )
        data = pd.DataFrame(
            [
                [
                    datetime.fromtimestamp(row[0], timezone.utc),
                    datetime.fromtimestamp(row[1], timezone.utc),
                    row[2],
                    row[3],
                    row[4],
                    row[5],
                ]
                for row in self.cur.fetchall()
            ],
            columns=[
                "export_date",
                "interval_start",
                "interval_period",
                "transmission_risk_level",
                "report_type",
                "days_since_onset_of_symptoms",
            ],
        )
        return data

    def risky_venues(self):
        self.cur.execute(
            """SELECT export_date, id, risky_from, risky_until, message_type
                            FROM risky_venues"""
        )
        data = pd.DataFrame(
            self.cur.fetchall(),
            columns=["export_date", "id", "risky_from", "risky_until", "message_type"],
        )

        data['export_date'] = pd.to_datetime(data['export_date'], unit='s')
        data['risky_from'] = pd.to_datetime(data['risky_from'], unit='s')
        data['risky_until'] = pd.to_datetime(data['risky_until'], unit='s')
        return data
