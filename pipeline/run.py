"""Run connectors, write silver/gold tables and the dashboard JSON.

    python -m pipeline.run                # all sources
    python -m pipeline.run msd_benefits   # one or more sources
    python -m pipeline.run --build-only   # rebuild gold + dashboard from existing silver

A failing connector never wipes data: its last good silver CSV is kept and the
status file marks it stale, so the dashboard keeps working and shows the problem.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib
import json
import logging
import shutil
import sys
from pathlib import Path

import pandas as pd
import yaml

from .core import COLUMNS, GOLD_DIR, MANUAL_DIR, ROOT, SILVER_DIR, SITE_DATA, RunResult, SourceBlocked, to_frame, write_json

SOURCES = ["statsnz_ade", "msd_benefits", "hud_housing", "healthnz_immunisation", "nzta_cas", "mbie_bonds",
           "statsnz_emissions", "moe_attendance", "statsnz_regional_gdp", "hud_affordability", "hud_urban_land", "moe_leavers",
           "statsnz_monthly", "mbie_accommodation", "statsnz_census_households", "ea_residential",
           "statsnz_vital_statistics", "moe_rolls_ece", "statsnz_river_quality", "statsnz_council_finance",
           "moe_school_discipline", "lawa_swimming", "lawa_groundwater", "moe_maori_medium", "statsnz_sa2", "nzqa_secondary",
           "statsnz_agriculture", "statsnz_leed", "nzta_mvr", "nzta_traffic", "moj_courts",
           "healthnz_hpv", "healthnz_pho_enrolment", "moh_nzhs_regional"]
MODULES = {
    "statsnz_ade": "statsnz_ade", "msd_benefits": "msd_benefits", "hud_housing": "hud_housing",
    "healthnz_immunisation": "healthnz_immunisation", "nzta_cas": "nzta_cas", "mbie_bonds": "mbie_bonds",
    "statsnz_emissions": "statsnz_emissions", "moe_attendance": "moe_attendance",
    "statsnz_regional_gdp": "statsnz_regional_gdp", "hud_affordability": "hud_affordability", "moe_leavers": "moe_leavers",
    "hud_urban_land": "hud_urban_land",
    "statsnz_monthly": "statsnz_monthly", "mbie_accommodation": "mbie_accommodation",
    "statsnz_census_households": "statsnz_census_households",
    "ea_residential": "ea_residential",
    "statsnz_vital_statistics": "statsnz_vital_statistics", "moe_rolls_ece": "moe_rolls_ece",
    "statsnz_river_quality": "statsnz_river_quality",
    "statsnz_council_finance": "statsnz_council_finance",
    "moe_school_discipline": "moe_school_discipline",
    "lawa_swimming": "lawa_swimming",
    "lawa_groundwater": "lawa_groundwater",
    "moe_maori_medium": "moe_maori_medium",
    "statsnz_sa2": "statsnz_sa2",
    "nzqa_secondary": "nzqa_secondary",
    "statsnz_agriculture": "statsnz_agriculture",
    "statsnz_leed": "statsnz_leed",
    "nzta_mvr": "nzta_mvr", "nzta_traffic": "nzta_traffic", "moj_courts": "moj_courts",
    "healthnz_hpv": "healthnz_hpv",
    "healthnz_pho_enrolment": "healthnz_pho_enrolment",
    "moh_nzhs_regional": "moh_nzhs_regional",
}
STATUS_FILE = ROOT / "data" / "status.json"
OBSERVATION_KEY = ["source_id", "indicator_id", "geo_type", "geo_code", "ethnicity", "age", "sex",
                   "period_start", "period_end"]
DOWNLOADS = ("observations.csv", "indicators.csv")
log = logging.getLogger("pipeline")


def run_source(sid: str) -> RunResult:
    mod = importlib.import_module(f"pipeline.sources.{MODULES[sid]}")
    try:
        rows, files = mod.run()
        df = to_frame(rows)
        if df.empty:
            raise RuntimeError("connector returned no rows")
        df = df.sort_values(["indicator_id", "geo_code", "ethnicity", "period_end"])
        out = SILVER_DIR / f"{sid}.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        _write_keeping_vintage(df, out)
        return RunResult(sid, True, len(df), df.period_end.max(), "ok", files)
    except SourceBlocked as e:
        return RunResult(sid, False, message=f"blocked: {e}")
    except Exception as e:  # keep running other sources
        log.exception("source %s failed", sid)
        return RunResult(sid, False, message=f"error: {e}")


def _write_keeping_vintage(new: pd.DataFrame, path) -> None:
    """Keep each row's original vintage_date unless its value changed (revision)."""
    if path.exists():
        old = pd.read_csv(path, dtype=str, keep_default_na=False)
        old["value"] = pd.to_numeric(old["value"], errors="coerce")
        merged = new.merge(old[OBSERVATION_KEY + ["value", "vintage_date"]], on=OBSERVATION_KEY,
                           how="left", suffixes=("", "_old"))
        same = (merged["value"] == merged["value_old"]) | (merged["value"].isna() & merged["value_old"].isna())
        merged.loc[same & merged["vintage_date_old"].ne(""), "vintage_date"] = merged["vintage_date_old"]
        new = merged[COLUMNS]
    new.to_csv(path, index=False)


def validate_observations(observations: pd.DataFrame, registry: dict) -> None:
    duplicates = observations.duplicated(OBSERVATION_KEY, keep=False)
    if duplicates.any():
        first = observations.loc[duplicates, OBSERVATION_KEY].iloc[0].to_dict()
        raise ValueError(f"Duplicate observation key: {first}")
    for column, field in (("indicator_id", "indicators"), ("source_id", "sources")):
        unknown = set(observations[column]) - registry[field].keys()
        if unknown:
            raise ValueError(f"Unregistered {column}: {sorted(unknown, key=str)}")
    suppressed = observations["suppression_flag"].fillna("").str.strip().ne("")
    if (suppressed & observations["value"].notna()).any():
        raise ValueError("Suppressed observations must have an empty value")


def build() -> None:
    reg = yaml.safe_load((ROOT / "pipeline" / "registry.yaml").read_text(encoding="utf-8"))
    status = json.loads(STATUS_FILE.read_text()) if STATUS_FILE.exists() else {}
    frames = [pd.read_csv(p, dtype={"geo_code": str}, keep_default_na=False, na_values=[""])
              for p in sorted(SILVER_DIR.glob("*.csv"))]
    obs = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=COLUMNS)
    obs["value"] = pd.to_numeric(obs["value"], errors="coerce")
    for c in ("suppression_flag", "quality_flag"):
        obs[c] = obs[c].astype("string").fillna("")
    validate_observations(obs, reg)
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    obs.to_csv(GOLD_DIR / "observations.csv", index=False)

    inds = reg["indicators"]
    meta = pd.DataFrame([{"indicator_id": k, **{f: v.get(f, "") for f in
                         ("name", "domain", "topic", "direction", "headline", "format", "caveat", "display")}}
                         for k, v in inds.items()])
    meta.to_csv(GOLD_DIR / "indicators.csv", index=False)

    # Dashboard JSON: compact series per indicator × geography × ethnicity.
    series = []
    for (ind, geo_type, geo, eth), g in obs.groupby(["indicator_id", "geo_type", "geo_code", "ethnicity"], sort=False):
        if ind not in inds:
            continue
        g = g.sort_values("period_end")
        digits = inds[ind].get("decimals", 2)
        series.append({
            "indicator": ind, "geo": geo, "geo_type": geo_type, "geo_name": g.geo_name.iloc[0], "ethnicity": eth,
            "source": g.source_id.iloc[0], "period_type": g.period_type.iloc[0],
            "unit": g.unit.iloc[0],
            "points": [[r.period_end, None if pd.isna(r.value) else round(float(r.value), digits),
                        r.suppression_flag or r.quality_flag or None] for r in g.itertuples()],
        })
        if g.period_type.iloc[0] == "multi_year":
            series[-1]["period_start"] = g.period_start.iloc[0]
    payload = {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "indicators": inds, "sources": reg["sources"], "series": series, "status": status,
        "catalogue": yaml.safe_load((ROOT / "pipeline" / "catalogue.yaml").read_text(encoding="utf-8")),
    }
    write_json(SITE_DATA / "dashboard.json", payload)
    for filename in DOWNLOADS:
        shutil.copyfile(GOLD_DIR / filename, SITE_DATA / filename)
    print(f"built: {len(obs)} observations, {len(series)} series")


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("sources", nargs="*", default=SOURCES)
    ap.add_argument("--build-only", action="store_true")
    ap.add_argument("--scheduled", action="store_true", help="respect per-source refresh intervals")
    a = ap.parse_args(argv)
    unknown = set(a.sources) - MODULES.keys()
    if unknown:
        ap.error(f"unknown source(s): {', '.join(sorted(unknown))}")
    if not a.build_only:
        status = json.loads(STATUS_FILE.read_text()) if STATUS_FILE.exists() else {}
        registry = yaml.safe_load((ROOT / "pipeline" / "registry.yaml").read_text(encoding="utf-8"))
        for sid in a.sources:
            prev = status.get(sid, {})
            days = registry["sources"][sid].get("check_every_days", 0)
            if a.scheduled and days and prev.get("ok") and prev.get("checked") and (SILVER_DIR / f"{sid}.csv").exists():
                checked = dt.datetime.fromisoformat(prev["checked"])
                if dt.datetime.now(dt.timezone.utc) - checked < dt.timedelta(days=days):
                    print(f"{sid:24s} SKIP checked within {days} days")
                    continue
            res = run_source(sid)
            d = res.as_dict()
            d.pop("files")
            if not res.ok:  # keep last-good facts, flag as stale
                d["rows"] = prev.get("rows", 0)
                d["latest_period"] = prev.get("latest_period")
                d["last_success"] = prev.get("last_success")
                if "schema_hash" in prev:
                    d["schema_hash"] = prev["schema_hash"]
                if "mode" in prev:
                    d["mode"] = prev["mode"]
            else:
                d["last_success"] = d["checked"]
                if any(Path(path).resolve().is_relative_to(MANUAL_DIR.resolve()) for path in res.files):
                    d["mode"] = "manual"
                    d["message"] = "ok – published from reviewed publisher files"
                # schema hash: alerts us when a publisher changes layout/indicators
                df = pd.read_csv(SILVER_DIR / f"{sid}.csv", usecols=["indicator_id", "geo_code", "ethnicity"])
                d["schema_hash"] = hashlib.sha1(
                    ",".join(sorted(set(map(str, df.itertuples(index=False))))).encode()).hexdigest()[:10]
                if prev.get("schema_hash") and prev["schema_hash"] != d["schema_hash"]:
                    d["message"] += " – indicator set changed since last run; check the connector"
            status[sid] = d
            print(f"{sid:24s} {'OK ' if res.ok else 'FAIL'} rows={d['rows']} latest={d['latest_period']} {res.message[:150]}")
        write_json(STATUS_FILE, status)
    build()
    return 0


if __name__ == "__main__":
    sys.exit(main())
