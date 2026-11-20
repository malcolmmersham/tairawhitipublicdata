# Manual drop folder

Some publishers block automated downloads from cloud servers. For those sources a data
steward saves the file here in a normal browser. The next scheduled run picks up the
newest file in the folder automatically.

| Folder | Source | What to save |
|---|---|---|
| `mbie_bonds/` | [MBIE rental bond data](https://www.mbie.govt.nz/building-and-energy/tenancy-and-housing/rental-bond-data/) | The **territorial authority, monthly** CSV. Name it `YYYY-MM-DD.csv` (download date). |

If you find the direct CSV URL, set it as the repository variable `MBIE_BOND_CSV_URL`
instead, and the workflow will try it first.
