"""
Draft pick handling for the trade simulator.

Future pick ownership is not published in any free feed, so the simulator
assumes each team holds its own pick in every round of the next three drafts.
Pick value uses an approximate Jimmy Johnson value at each round's midpoint with
a discount for picks further out, since the exact slot is unknown until the
season plays out.
"""

import datetime

# Approx Jimmy Johnson trade value at each round's midpoint (32 teams).
ROUND_VALUE = {1: 1000, 2: 420, 3: 185, 4: 70, 5: 35, 6: 20, 7: 12}
ROUND_LABEL = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th", 6: "6th", 7: "7th"}


def next_draft_year(today: datetime.date | None = None) -> int:
    """The next draft that can still be traded (the NFL draft is in April)."""
    today = today or datetime.date.today()
    return today.year + 1 if today.month >= 5 else today.year


def pick_value(year: int, rnd: int, base_year: int) -> float:
    base = ROUND_VALUE.get(rnd, 5)
    years_out = max(0, year - base_year)
    return round(base * (0.85 ** years_out), 1)


def pick_label(year: int, rnd: int) -> str:
    return f"{year} {ROUND_LABEL.get(rnd, str(rnd))}"


def team_pick_options(base_year: int | None = None, drafts: int = 3) -> list[str]:
    """Pick labels a team is assumed to own, for the next `drafts` drafts."""
    base_year = base_year or next_draft_year()
    return [pick_label(y, r) for y in range(base_year, base_year + drafts) for r in range(1, 8)]


def parse_pick(label: str):
    """'2027 1st' -> (2027, 1)."""
    try:
        year_str, rnd_str = label.split(" ", 1)
        rnd = next(r for r, lbl in ROUND_LABEL.items() if lbl == rnd_str.strip())
        return int(year_str), rnd
    except Exception:
        return None, None


def picks_value(labels: list[str], base_year: int | None = None) -> float:
    base_year = base_year or next_draft_year()
    total = 0.0
    for lbl in labels:
        y, r = parse_pick(lbl)
        if y is not None:
            total += pick_value(y, r, base_year)
    return round(total, 1)
