import csv
import math
import statistics
from datetime import datetime
from collections import defaultdict


def parse_journeys(rows):
    journeys = {}
    skipped = 0

    for r in rows:
        afid   = r["AppsFlyer ID"]
        last_ms = r["Media Source"].strip()
        last_t  = r["Attributed Touch Time"].strip()

        try:
            fmt = "%Y-%m-%d %H:%M:%S" if len(last_t) >= 19 else "%Y-%m-%d %H:%M"
            t_last = datetime.strptime(last_t[:19], fmt)
        except Exception:
            t_last = None

        contributors = []
        for i in ["1", "2", "3"]:
            c_ms = r.get(f"Contributor {i} Media Source", "").strip()
            c_t  = r.get(f"Contributor {i} Touch Time", "").strip()
            if not c_ms:
                continue
            if t_last and c_t:
                try:
                    t_c = datetime.strptime(c_t[:19], "%Y-%m-%d %H:%M:%S")
                    if t_c >= t_last:
                        skipped += 1
                        continue
                    hours = (t_last - t_c).total_seconds() / 3600
                    contributors.append({"ms": c_ms, "hours": hours})
                except Exception:
                    contributors.append({"ms": c_ms, "hours": None})
            else:
                contributors.append({"ms": c_ms, "hours": None})

        with_t    = sorted([c for c in contributors if c["hours"] is not None], key=lambda x: -x["hours"])
        without_t = [c for c in contributors if c["hours"] is None]

        journeys[afid] = {
            "last": last_ms,
            "contributors": with_t + without_t,
            "install_time": r.get("Install Time", "").strip(),
        }

    return journeys, skipped


def compute_median_hours(journeys):
    all_hours = [
        c["hours"]
        for j in journeys.values()
        for c in j["contributors"]
        if c["hours"] is not None
    ]
    if not all_hours:
        return 6.0
    return statistics.median(all_hours)


def time_decay_weight(hours, h):
    if hours is None:
        return 0.5
    return math.pow(2, -hours / h)


def compute_credits(journeys, half_life, last_touch_half_life):
    lt_credits = defaultdict(float)
    td_credits = defaultdict(float)

    for j in journeys.values():
        last     = j["last"]
        contribs = j["contributors"]

        lt_credits[last] += 1.0

        if not contribs:
            td_credits[last] += 1.0
        else:
            valid_hours = [c["hours"] for c in contribs if c["hours"] is not None]
            span      = max(valid_hours) if valid_hours else 0
            min_hours = min(valid_hours) if valid_hours else 0

            last_w  = 1 - time_decay_weight(min_hours, last_touch_half_life)
            weights = {last: last_w}

            for c in contribs:
                w = time_decay_weight(c["hours"], span if span > 0 else half_life)
                weights[c["ms"]] = max(weights.get(c["ms"], 0), w)

            total_w = sum(weights.values())
            for ms, w in weights.items():
                td_credits[ms] += w / total_w

    return lt_credits, td_credits


def build_results(lt_credits, td_credits):
    total_lt = sum(lt_credits.values())
    total_td = sum(td_credits.values())

    all_channels = set(list(lt_credits.keys()) + list(td_credits.keys()))
    rows = []
    for ch in all_channels:
        lt_pct = lt_credits.get(ch, 0) / total_lt * 100
        td_pct = td_credits.get(ch, 0) / total_td * 100
        delta  = td_pct - lt_pct
        var    = (delta / lt_pct * 100) if lt_pct > 0 else 0
        rows.append({
            "channel":  ch,
            "lt_installs": round(lt_credits.get(ch, 0)),
            "lt_pct":   round(lt_pct, 2),
            "td_pct":   round(td_pct, 2),
            "delta":    round(delta, 2),
            "var_pct":  round(var, 1),
        })

    rows.sort(key=lambda x: -x["delta"])
    return rows
