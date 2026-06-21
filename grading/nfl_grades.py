"""
NFL player grading.

Veterans are scored 0-100 against position-group peers on a weighted blend of
advanced stats (Next Gen Stats, PFR advanced, QBR, EPA, production). Rookies,
who have no NFL snaps, are scored from their final college season (CFBD) plus
draft capital and combine testing. Offensive line and specialists are graded on
role and availability, since per-player production/win-rate data is not free.

Everything is defensive: any missing stat column is dropped from the blend and
the remaining weights renormalize, so a missing feed never counts as a zero.
"""

import re
import math
import pandas as pd

from grading.scale import percentile_scores, weighted_blend, to_letter, pick_curve

# Roster position -> grading group
GROUPS = {
    "QB": "QB",
    "RB": "RB", "FB": "RB", "HB": "RB",
    "WR": "WR",
    "TE": "TE",
    "T": "OL", "OT": "OL", "G": "OL", "OG": "OL", "C": "OL", "OL": "OL", "LT": "OL", "RT": "OL", "LG": "OL", "RG": "OL",
    "DE": "DL", "DT": "DL", "NT": "DL", "DL": "DL", "EDGE": "DL",
    "LB": "LB", "ILB": "LB", "OLB": "LB", "MLB": "LB",
    "CB": "DB", "DB": "DB", "S": "DB", "FS": "DB", "SS": "DB",
    "K": "ST", "P": "ST", "LS": "ST",
}
PRODUCTION_GROUPS = {"QB", "RB", "WR", "TE", "DL", "LB", "DB"}
ROLE_GROUPS = {"OL", "ST"}


def group_for(position: str) -> str:
    if not isinstance(position, str):
        return "OTHER"
    return GROUPS.get(position.upper().strip(), "OTHER")


def _clean_name(s) -> str:
    if not isinstance(s, str):
        return ""
    s = s.lower()
    s = re.sub(r"[.\,']", "", s)
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", s)
    return re.sub(r"\s+", " ", s).strip()


def _num(df, col):
    return pd.to_numeric(df[col], errors="coerce") if col in df.columns else pd.Series([float("nan")] * len(df), index=df.index)


def _merge_name(base: pd.DataFrame, other: pd.DataFrame, take: list[str], name_other: str) -> pd.DataFrame:
    """Left-merge selected columns from `other` onto `base` by cleaned name."""
    if other is None or other.empty or name_other not in other.columns:
        return base
    o = other.copy()
    o["_k"] = o[name_other].map(_clean_name)
    cols = [c for c in take if c in o.columns]
    if not cols:
        return base
    o = o.dropna(subset=["_k"]).drop_duplicates("_k", keep="first")[["_k"] + cols]
    base = base.copy()
    base["_k"] = base["player_name"].map(_clean_name)
    merged = base.merge(o, on="_k", how="left", suffixes=("", "_x")).drop(columns="_k")
    return merged


# ── Veteran position recipes ─────────────────────────────────────────
# component -> (column, higher_is_better, weight). Derived columns (ypc, prod_*)
# are computed in _prepare before grading.
RECIPES = {
    "QB": {
        "epa": ("passing_epa", True, .22),
        "cpoe": ("completion_percentage_above_expectation", True, .18),
        "qbr": ("qbr_total", True, .20),
        "prod": ("prod_pass", True, .22),
        "security": ("interceptions", False, .18),
    },
    "RB": {
        "ryoe": ("rush_yards_over_expected_per_att", True, .22),
        "epa": ("rushing_epa", True, .16),
        "prod": ("prod_rush", True, .24),
        "rec": ("prod_rbrec", True, .18),
        "eff": ("ypc", True, .20),
    },
    "WR": {
        "prod": ("prod_rec", True, .26),
        "epa": ("receiving_epa", True, .18),
        "sep": ("avg_separation", True, .16),
        "yacoe": ("avg_yac_above_expectation", True, .14),
        "usage": ("usage_rec", True, .14),
        "eff": ("ypr", True, .12),
    },
    "TE": {
        "prod": ("prod_rec", True, .28),
        "epa": ("receiving_epa", True, .18),
        "sep": ("avg_separation", True, .16),
        "usage": ("usage_rec", True, .16),
        "eff": ("ypr", True, .22),
    },
    "DL": {
        "sacks": ("v_sacks", True, .34),
        "pressures": ("v_pressures", True, .30),
        "run": ("v_tfl", True, .20),
        "tackles": ("v_tackles", True, .16),
    },
    "LB": {
        "tackles": ("v_tackles", True, .30),
        "pressures": ("v_pressures", True, .22),
        "cover": ("v_passdef", True, .24),
        "run": ("v_tfl", True, .24),
    },
    "DB": {
        "cover": ("v_passdef", True, .40),
        "ballhawk": ("v_int", True, .24),
        "tackles": ("v_tackles", True, .20),
        "pressures": ("v_pressures", True, .16),
    },
}


def _prepare(table: pd.DataFrame) -> pd.DataFrame:
    """Compute derived columns used by the recipes."""
    t = table.copy()
    car = _num(t, "carries")
    rec = _num(t, "receptions")
    rec_yds = _num(t, "receiving_yards")

    t["prod_pass"] = _num(t, "passing_yards").fillna(0) + 25 * _num(t, "passing_tds").fillna(0)
    t["prod_rush"] = _num(t, "rushing_yards").fillna(0) + 25 * _num(t, "rushing_tds").fillna(0)
    t["prod_rbrec"] = rec_yds.fillna(0) + 10 * rec.fillna(0)
    t["prod_rec"] = rec_yds.fillna(0) + 25 * _num(t, "receiving_tds").fillna(0)
    t["usage_rec"] = _num(t, "target_share")
    if t["usage_rec"].isna().all():
        t["usage_rec"] = _num(t, "targets")
    t["ypc"] = (_num(t, "rushing_yards") / car).where(car > 0)
    t["ypr"] = (rec_yds / rec).where(rec > 0)

    # Defensive production: prefer player_stats def_* then PFR def_*
    t["v_sacks"] = _num(t, "def_sacks")
    if t["v_sacks"].isna().all():
        t["v_sacks"] = _num(t, "sacks")
    t["v_tackles"] = _num(t, "def_tackles")
    if t["v_tackles"].isna().all():
        t["v_tackles"] = _num(t, "comb")  # PFR combined tackles
    t["v_tfl"] = _num(t, "def_tackles_for_loss")
    if t["v_tfl"].isna().all():
        t["v_tfl"] = _num(t, "tfl")
    t["v_passdef"] = _num(t, "def_pass_defended")
    if t["v_passdef"].isna().all():
        t["v_passdef"] = _num(t, "pass_defended")
    t["v_int"] = _num(t, "def_interceptions")
    if t["v_int"].isna().all():
        t["v_int"] = _num(t, "int")
    # Pressures: PFR def has hurries/hits/pressures depending on version
    pres = _num(t, "pressures")
    if pres.isna().all():
        pres = _num(t, "qb_hits").fillna(0) + _num(t, "hurries").fillna(0) + _num(t, "v_sacks").fillna(0)
        pres = pres.where(pres > 0)
    t["v_pressures"] = pres
    return t


def _grade_group(sub: pd.DataFrame, recipe: dict) -> pd.Series:
    """Return a 0-100 grade series for one position group."""
    pct = {}
    for comp, (col, higher, _w) in recipe.items():
        pct[comp] = percentile_scores(_num(sub, col), higher_is_better=higher)
    weights = {comp: w for comp, (_c, _h, w) in recipe.items()}
    grades = []
    for i in sub.index:
        comps = {c: pct[c][i] for c in recipe}
        grades.append(weighted_blend(comps, weights))
    return pd.Series(grades, index=sub.index)


# ── Role-based grading (OL / ST) ─────────────────────────────────────

def _grade_role(sub: pd.DataFrame, team_protection: pd.Series | None) -> pd.Series:
    """
    OL/ST grade from snaps (entrenchment/availability) blended with a team
    pass-protection factor for OL. Clearly an availability proxy, not production.
    """
    snaps = _num(sub, "offense_snaps")
    if snaps.isna().all():
        snaps = _num(sub, "snaps")
    p_snaps = percentile_scores(snaps)
    grades = []
    for i in sub.index:
        comps = {"snaps": p_snaps[i]}
        weights = {"snaps": 1.0}
        if team_protection is not None and i in team_protection.index and not math.isnan(team_protection[i]):
            comps["prot"] = team_protection[i]
            weights = {"snaps": .55, "prot": .45}
        grades.append(weighted_blend(comps, weights))
    return pd.Series(grades, index=sub.index)


# ── Rookie grading ───────────────────────────────────────────────────

def _college_score(sub: pd.DataFrame) -> pd.Series:
    """Percentile of college production within the rookie's position group."""
    grp = sub["group"].iloc[0] if len(sub) else "OTHER"
    if grp == "QB":
        raw = _num(sub, "pass_yds").fillna(0) + 25 * _num(sub, "pass_td").fillna(0) - 20 * _num(sub, "pass_int").fillna(0)
    elif grp == "RB":
        raw = _num(sub, "rush_yds").fillna(0) + 25 * _num(sub, "rush_td").fillna(0) + 5 * _num(sub, "rec").fillna(0)
    elif grp in ("WR", "TE"):
        raw = _num(sub, "rec_yds").fillna(0) + 25 * _num(sub, "rec_td").fillna(0)
    elif grp == "DL":
        raw = 10 * _num(sub, "sacks").fillna(0) + 4 * _num(sub, "tfl").fillna(0) + _num(sub, "tackles").fillna(0)
    elif grp == "LB":
        raw = _num(sub, "tackles").fillna(0) + 4 * _num(sub, "tfl").fillna(0) + 6 * _num(sub, "sacks").fillna(0) + 5 * _num(sub, "pass_def").fillna(0)
    elif grp == "DB":
        raw = _num(sub, "tackles").fillna(0) + 8 * _num(sub, "def_int").fillna(0) + 5 * _num(sub, "pass_def").fillna(0)
    else:
        return pd.Series([float("nan")] * len(sub), index=sub.index)
    # If the whole group has no college data, return NaN (renormalizes out)
    if raw.fillna(0).sum() == 0:
        return pd.Series([float("nan")] * len(sub), index=sub.index)
    return percentile_scores(raw)


def _combine_score(sub: pd.DataFrame) -> pd.Series:
    """Athletic score from combine testing, percentile within group."""
    forty = percentile_scores(_num(sub, "forty"), higher_is_better=False)
    vert = percentile_scores(_num(sub, "vertical"))
    broad = percentile_scores(_num(sub, "broad_jump"))
    cone = percentile_scores(_num(sub, "cone"), higher_is_better=False)
    shuttle = percentile_scores(_num(sub, "shuttle"), higher_is_better=False)
    bench = percentile_scores(_num(sub, "bench"))
    out = []
    for i in sub.index:
        comps = {"forty": forty[i], "vert": vert[i], "broad": broad[i],
                 "cone": cone[i], "shuttle": shuttle[i], "bench": bench[i]}
        out.append(weighted_blend(comps, {"forty": .3, "vert": .2, "broad": .15, "cone": .15, "shuttle": .1, "bench": .1}))
    return pd.Series(out, index=sub.index)


def grade_rookies(rookies: pd.DataFrame) -> pd.Series:
    """
    Grade rookies from college production + draft capital + combine.
    `rookies` must carry: group, draft_pick (NaN if UDFA), college stat columns,
    and combine columns (all optional).
    """
    if rookies.empty:
        return pd.Series([], dtype=float)

    out = pd.Series([float("nan")] * len(rookies), index=rookies.index)
    draft = pd.Series([pick_curve(p) for p in _num(rookies, "draft_pick")], index=rookies.index)
    # Undrafted: floor capital score
    udfa = _num(rookies, "draft_pick").isna()
    draft[udfa] = 35.0

    for grp, idx in rookies.groupby("group").groups.items():
        sub = rookies.loc[idx]
        college = _college_score(sub)
        combine = _combine_score(sub)
        is_role = grp in ROLE_GROUPS or grp == "OTHER"
        for i in sub.index:
            if is_role:
                comps = {"draft": draft[i], "combine": combine[i]}
                weights = {"draft": .65, "combine": .35}
            else:
                comps = {"college": college[i], "draft": draft[i], "combine": combine[i]}
                weights = {"college": .45, "draft": .35, "combine": .20}
            out[i] = weighted_blend(comps, weights)
    return out


# ── Top-level orchestration ──────────────────────────────────────────

def build_player_table(inputs: dict) -> pd.DataFrame:
    """Merge rosters + production + advanced feeds into one graded-ready table."""
    rosters = inputs.get("rosters", pd.DataFrame()).copy()
    if rosters.empty:
        return pd.DataFrame()

    # Normalize roster columns
    name_col = "player_name" if "player_name" in rosters.columns else ("full_name" if "full_name" in rosters.columns else None)
    if name_col and name_col != "player_name":
        rosters = rosters.rename(columns={name_col: "player_name"})
    rosters["group"] = rosters["position"].map(group_for) if "position" in rosters.columns else "OTHER"

    base = rosters
    # Production by gsis id
    ps = inputs.get("player_stats", pd.DataFrame())
    if not ps.empty:
        ps = ps.rename(columns={"player_id": "gsis_id"}) if "player_id" in ps.columns else ps
        prod_cols = [c for c in ps.columns if c not in base.columns or c == "gsis_id"]
        if "gsis_id" in base.columns and "gsis_id" in ps.columns:
            base = base.merge(ps[prod_cols], on="gsis_id", how="left", suffixes=("", "_ps"))

    # Advanced feeds by name
    base = _merge_name(base, inputs.get("ngs_passing", pd.DataFrame()),
                       ["completion_percentage_above_expectation", "avg_time_to_throw", "passer_rating"], "player_display_name")
    base = _merge_name(base, inputs.get("ngs_rushing", pd.DataFrame()),
                       ["rush_yards_over_expected_per_att", "efficiency"], "player_display_name")
    base = _merge_name(base, inputs.get("ngs_receiving", pd.DataFrame()),
                       ["avg_separation", "avg_yac_above_expectation", "avg_cushion"], "player_display_name")
    base = _merge_name(base, inputs.get("qbr", pd.DataFrame()), ["qbr_total"], "name_display")
    base = _merge_name(base, inputs.get("pfr_def", pd.DataFrame()),
                       ["pressures", "qb_hits", "hurries", "comb", "tfl", "pass_defended", "int", "sacks"], "pfr_player_name")
    base = _merge_name(base, inputs.get("snaps", pd.DataFrame()),
                       ["offense_snaps", "defense_snaps", "st_snaps"], "player")
    return base


def grade_all(inputs: dict, college_wide: pd.DataFrame | None = None) -> pd.DataFrame:
    """Return the full roster graded: veterans + rookies, with grade/letter/group."""
    table = build_player_table(inputs)
    if table.empty:
        return table

    table = _prepare(table)
    table["rookie"] = (_num(table, "years_exp").fillna(99) == 0)

    # Draft pick for rookies
    draft = inputs.get("draft", pd.DataFrame())
    if not draft.empty:
        dcol = "pfr_player_name" if "pfr_player_name" in draft.columns else ("player_name" if "player_name" in draft.columns else None)
        if dcol:
            d = draft.copy()
            d["_k"] = d[dcol].map(_clean_name)
            pick_col = "pick" if "pick" in d.columns else ("overall" if "overall" in d.columns else None)
            if pick_col:
                d = d.dropna(subset=["_k"]).drop_duplicates("_k")[["_k", pick_col]].rename(columns={pick_col: "draft_pick"})
                table["_k"] = table["player_name"].map(_clean_name)
                table = table.merge(d, on="_k", how="left").drop(columns="_k")
    if "draft_pick" not in table.columns:
        table["draft_pick"] = float("nan")

    # Combine for rookies
    combine = inputs.get("combine", pd.DataFrame())
    if not combine.empty and "player_name" in combine.columns:
        table = _merge_name(table, combine, ["forty", "vertical", "broad_jump", "cone", "shuttle", "bench"], "player_name")

    # College stats for rookies (matched by name + college)
    if college_wide is not None and not college_wide.empty:
        cw = college_wide.copy()
        cw["_k"] = cw["player"].map(_clean_name)
        stat_cols = [c for c in cw.columns if c not in ("player", "player_id", "college", "conference", "_k")]
        cw = cw.dropna(subset=["_k"]).drop_duplicates("_k")[["_k"] + stat_cols]
        table["_k"] = table["player_name"].map(_clean_name)
        table = table.merge(cw, on="_k", how="left").drop(columns="_k")

    table["grade"] = float("nan")
    table["graded_as"] = ""

    # Team pass-protection factor for OL (team sacks allowed/game, inverted)
    team_prot = _team_protection_factor(inputs, table)

    for grp, idx in table.groupby("group").groups.items():
        sub = table.loc[idx]
        vets = sub[~sub["rookie"]]
        rks = sub[sub["rookie"]]

        if grp in PRODUCTION_GROUPS:
            if not vets.empty:
                g = _grade_group(vets, RECIPES[grp])
                table.loc[g.index, "grade"] = g.values
                table.loc[g.index, "graded_as"] = "production"
        elif grp in ROLE_GROUPS:
            g = _grade_role(sub, team_prot)
            table.loc[g.index, "grade"] = g.values
            table.loc[g.index, "graded_as"] = "role"

        if not rks.empty:
            rg = grade_rookies(rks)
            table.loc[rg.index, "grade"] = rg.values
            table.loc[rg.index, "graded_as"] = "rookie"

    table["letter"] = table["grade"].map(to_letter)
    return table


def _team_protection_factor(inputs: dict, table: pd.DataFrame) -> pd.Series:
    """Map each OL row to a 0-100 score from its team's sacks allowed per game."""
    sched = inputs.get("schedules", pd.DataFrame())
    if sched.empty or "team" not in table.columns:
        return pd.Series(dtype=float)
    # Without play-level sack-allowed data wired here, return neutral (NaN).
    # Hook left for a future team pass-block feed; OL falls back to snaps only.
    return pd.Series(dtype=float)
