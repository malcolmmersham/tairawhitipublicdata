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
| `lawa_swimming/` | [LAWA recreational water quality download](https://www.lawa.org.nz/download-data) | Review the workbook's Dataset Notices and row licences. From MonitoringData, select the Gisborne region, Gisborne District Council, Routine, and the River/E. coli and Coastal/Enterococci pairs. Keep the columns in the bundled extract, write SampleDate as YYYY-MM-DD, and save as `gisborne-swimming-samples-YYYY-MM-DD.csv` using the publisher's release date. Run `python -m pipeline.run lawa_swimming`. |
| `lawa_groundwater/` | [LAWA groundwater quality download](https://www.lawa.org.nz/download-data) | Review the workbook's Dataset Notices and the `DataLicensing` column. From the MonitoringData sheet, keep rows where Region is Gisborne, Agency is Gisborne District Council and DataLicensing is `CC BY 4.0`. Keep the columns in the bundled extract, leave `Value` as published (for example `<0.002`), write SampleDateTime as `YYYY-MM-DDTHH:MM:SS`, and save as `gisborne-groundwater-samples-YYYY-MM-DD.csv` using the publisher's release date. Remove the superseded extract and run `python -m pipeline.run lawa_groundwater`. |

The LAWA extract uses the [3 November 2026 workbook](https://www.lawa.org.nz/media/0ywltdvh/lawa-recreational-water-quality-monitoring-data-2020-2026_3nov2026.xlsx).
LAWA and Gisborne District Council supply the samples under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
The extract selects local routine monitoring records and standardises dates. The observations CSV
represents a lab reporting limit as the numeric boundary with a `less_than` or `greater_than` quality flag.

The groundwater extract uses the [27 October 2026 workbook](https://www.lawa.org.nz/media/thscdkke/lawa-groundwater-quality-dataset_27oct2026.xlsx)
(SHA-256 `5be4feeb9f60dee0d6be9f3f93d4202f46b7ef072c18629861226197697dfeab`). Its MonitoringData sheet has
10,281 Gisborne District Council rows. The extract keeps the 9,762 rows from 57 bores licensed CC BY 4.0
and leaves out the 519 rows from 22 bores whose licence is `Unstated`. Each observation is keyed by LAWA
site ID, indicator and sample time, because some bores were sampled twice on one day. Times are kept as
supplied, since the notices say they may be NZST, NZDT or UTC. The connector stops if a row is unlicensed,
duplicated, or has an unexpected unit or censor symbol. LAWA's state and trend sheets are not published here.
The [2 November 2026 lake workbook](https://www.lawa.org.nz/media/ksjfr5ug/lawa-lake-quality-dataset_2nov2026.xlsx)
has no Gisborne rows, so there is no lake extract.

Population projections use the reviewed Gisborne Region low, medium and high rows in Table 1 of
the [Stats NZ 2023-base workbook](https://www.stats.govt.nz/information-releases/subnational-population-projections-2023base-2053/).
On the next base release, review the new assumptions and publish the official scenario values in
the silver table. Keep projected values separate from observed population estimates.

The bundled Education Counts workbooks are public releases from the Ministry of Education,
licensed under CC BY 4.0. Review new workbooks and replace superseded files as the publisher releases them.

If you find the direct CSV URL, set it as the repository variable `MBIE_BOND_CSV_URL`
instead, and the workflow will try it first.
