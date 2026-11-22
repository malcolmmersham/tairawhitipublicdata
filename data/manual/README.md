# Manual drop folder

Some publishers block automated downloads from cloud servers. For those sources a data
steward saves the file here in a normal browser. The next scheduled run picks up the
newest file in the folder automatically.

| Folder | Source | What to save |
|---|---|---|
| `mbie_bonds/` | [Tenancy Services rental bond data](https://www.tenancy.govt.nz/about-tenancy-services/data-and-statistics/rental-bond-data/) | The **territorial authority, monthly** CSV. Name it `YYYY-MM-DD.csv` (download date). |
| `moe_attendance/` | [Education Counts regular attendance](https://www.educationcounts.govt.nz/statistics/attendance) | Download both the 2019–2021 and latest 2022 onward termly XLSX workbooks and keep their publisher filenames. Run `python -m pipeline.run moe_attendance`. |
| `moe_leavers/` | [Education Counts school leavers](https://www.educationcounts.govt.nz/statistics/school-leavers) | Save the latest Level 2 time-series XLSX with its publisher filename. Run `python -m pipeline.run moe_leavers`. |
| `moe_rolls_ece/` | [School rolls](https://www.educationcounts.govt.nz/statistics/school-rolls) and [prior early learning participation](https://www.educationcounts.govt.nz/statistics/participation) | Save the latest school rolls trend XLSX and prior participation year-ended XLSX with publisher filenames. Run `python -m pipeline.run moe_rolls_ece`. |
| `moe_school_discipline/` | [Education Counts disciplinary decisions](https://www.educationcounts.govt.nz/statistics/stand-downs%2C-suspensions%2C-exclusions-and-expulsions) | Save the four time-series workbooks for stand-downs, suspensions, exclusions and expulsions with their publisher filenames. Run `python -m pipeline.run moe_school_discipline`. |
| `moe_maori_medium/` | [Education Counts Māori language in schooling](https://www.educationcounts.govt.nz/statistics/maori-language-in-schooling) | Save **Pivot table: Student numbers** with its publisher filename. Run `python -m pipeline.run moe_maori_medium`. The connector selects Gisborne District school locations and immersion levels 1 and 2. |
| `moe_tertiary/` | [Education Counts tertiary participation](https://www.educationcounts.govt.nz/statistics/tertiary-participation) | Open the latest workbook that reports domestic tertiary students and participation rates by **region of residence** (not provider location). Copy every published Gisborne Region year into `tertiary-participation-region-YYYY-MM-DD.csv` (publisher release date) with the columns `Year,Region of residence,Age group,Domestic students,Participation rate (%),Publisher file,Publisher table`. Use one age group, keep the publisher's rounding, write a suppression symbol (such as `s`) as shown, and leave a cell blank only when it is not published. Run `python -m pipeline.run moe_tertiary`, then add `moe_tertiary` to `SOURCES` in `pipeline/run.py`. |
| `lawa_swimming/` | [LAWA recreational water quality download](https://www.lawa.org.nz/download-data) | Review the workbook's Dataset Notices and row licences. From MonitoringData, select the Gisborne region, Gisborne District Council, Routine, and the River/E. coli and Coastal/Enterococci pairs. Keep the columns in the bundled extract, write SampleDate as YYYY-MM-DD, and save as `gisborne-swimming-samples-YYYY-MM-DD.csv` using the publisher's release date. Run `python -m pipeline.run lawa_swimming`. |

The LAWA extract uses the [3 November 2026 workbook](https://www.lawa.org.nz/media/0ywltdvh/lawa-recreational-water-quality-monitoring-data-2020-2026_3nov2026.xlsx).
LAWA and Gisborne District Council supply the samples under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
The extract selects local routine monitoring records and standardises dates. The observations CSV
represents a lab reporting limit as the numeric boundary with a `less_than` or `greater_than` quality flag.

Population projections use the reviewed Gisborne Region low, medium and high rows in Table 1 of
the [Stats NZ 2023-base workbook](https://www.stats.govt.nz/information-releases/subnational-population-projections-2023base-2053/).
On the next base release, review the new assumptions and publish the official scenario values in
the silver table. Keep projected values separate from observed population estimates.

The bundled Education Counts workbooks are public releases from the Ministry of Education,
licensed under CC BY 4.0. Review new workbooks and replace superseded files as the publisher releases them.

If you find the direct CSV URL, set it as the repository variable `MBIE_BOND_CSV_URL`
instead, and the workflow will try it first.
