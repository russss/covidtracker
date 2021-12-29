import pandas as pd
import requests
import sqlite3
import tempfile
import json
from collections import defaultdict
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

    def home_test_availability(self):
        self.cur.execute("SELECT date, pcr_keyworker, pcr_public, lfd_public FROM home_test_availability")
        data = pd.DataFrame(self.cur.fetchall(),
                            columns=['date', 'pcr_keyworker', 'pcr_public', 'lfd_public'])
        data['date'] = pd.to_datetime(data['date'], unit='s')
        for field in ('pcr_keyworker', 'pcr_public', 'lfd_public'):
            data[field] = data[field] == 'OPEN'
        return data.set_index('date')

    def walk_in_availability(self):
        self.cur.execute("SELECT date, availability FROM walk_in_pcr_availability")
        data = defaultdict(list)
        for row in self.cur:
            availability = json.loads(row[1])
            date = pd.to_datetime(availability['lastUpdated']).tz_localize(None)
            for nation in availability['availability']:
                if 'items' not in nation:
                    # Scotland has no breakdown
                    data['date'].append(date)
                    data['area'].append(nation['name'])
                    data['availability'].append(nation['availability']['citizen'])
                else:
                    for region in nation['items']:
                        # Non-English nations have an "All regions" parent group for some reason.
                        if region['name'] == 'All regions':
                            name = nation['name']
                        else:
                            name = region['name']
                        data['date'].append(date)
                        data['area'].append(name)
                        data['availability'].append(region['availability']['citizen'])

        return pd.DataFrame.from_dict(data).set_index('date')
