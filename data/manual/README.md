# Manual drop folder

Some publishers block automated downloads from cloud servers. For those sources a data
steward saves the file here in a normal browser. The next scheduled run picks up the
newest file in the folder automatically.

| Folder | Source | What to save |
|---|---|---|
| `mbie_bonds/` | [Tenancy Services rental bond data](https://www.tenancy.govt.nz/about-tenancy-services/data-and-statistics/rental-bond-data/) | The **territorial authority, monthly** CSV. Name it `YYYY-MM-DD.csv` (download date). |
| `moe_attendance/` | [Education Counts regular attendance](https://www.educationcounts.govt.nz/statistics/attendance) | Download both the 2019–2021 and latest 2022 onward termly XLSX workbooks and keep their publisher filenames. Run `python -m pipeline.run moe_attendance`. |
| `moe_leavers/` | [Education Counts school leavers](https://www.educationcounts.govt.nz/statistics/school-leavers) | Save the latest Level 2 time-series XLSX with its publisher filename. Run `python -m pipeline.run moe_leavers`. |

The bundled Education Counts workbooks are public releases from the Ministry of Education,
licensed under CC BY 4.0. Review new workbooks and replace superseded files as the publisher releases them.

If you find the direct CSV URL, set it as the repository variable `MBIE_BOND_CSV_URL`
instead, and the workflow will try it first.
