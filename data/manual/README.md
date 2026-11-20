# Manual drop folder

Some publishers block automated downloads from cloud servers. For those sources a data
steward saves the file here in a normal browser. The next scheduled run picks up the
newest file in the folder automatically.

| Folder | Source | What to save |
|---|---|---|
| `mbie_bonds/` | [Tenancy Services rental bond data](https://www.tenancy.govt.nz/about-tenancy-services/data-and-statistics/rental-bond-data/) | The **territorial authority, monthly** CSV. Name it `YYYY-MM-DD.csv` (download date). |
| `moe_attendance/` | [Education Counts regular attendance](https://www.educationcounts.govt.nz/statistics/attendance) | Download both the 2019–2021 and latest 2022 onward termly XLSX workbooks and keep their publisher filenames. Run `python -m pipeline.run moe_attendance`. |

If you find the direct CSV URL, set it as the repository variable `MBIE_BOND_CSV_URL`
instead, and the workflow will try it first.
