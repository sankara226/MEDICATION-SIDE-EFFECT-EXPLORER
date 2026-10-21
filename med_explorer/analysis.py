"""Analysis functions on top of the openFDA client.

Each function returns (result, error) like the API client, so callers
can show a friendly message instead of crashing.
"""

import difflib
import math
from datetime import date

import pandas as pd

from .api import MAX_COUNT_LIMIT, fetch_openfda, is_not_found

SEX_LABELS = {0: "Unknown", 1: "Male", 2: "Female"}
WOMEN, MEN = 2, 1


# ---------------------------------------------------------------- searching

def build_search(drug, sex_code=None):
    search = f'patient.drug.openfda.generic_name:"{drug}"'
    if sex_code is not None:
        search += f" AND patient.patientsex:{sex_code}"
    return search


def count_reports(drug=None, sex_code=None):
    """Number of reports mentioning `drug` (whole database if drug is None).

    Returns (total, error). A search with no match gives (0, None).
    """
    params = {"limit": 1}
    if drug is not None:
        params["search"] = build_search(drug, sex_code)

    data, error = fetch_openfda(params)
    if is_not_found(error):
        return 0, None
    if error:
        return None, error
    return data["meta"]["results"]["total"], None


def get_drug_catalog(limit=MAX_COUNT_LIMIT):
    """The most reported generic names, used for 'did you mean' suggestions."""
    data, error = fetch_openfda({
        "count": "patient.drug.openfda.generic_name.exact",
        "limit": limit,
    })
    if error:
        return None, error

    catalog = pd.DataFrame(data["results"])
    catalog.columns = ["drug", "reports"]
    return catalog, None


def suggest_drug(name, catalog):
    if catalog is None:
        return []
    all_names = catalog["drug"].tolist()
    return difflib.get_close_matches(name.upper(), all_names, n=5, cutoff=0.6)


def resolve_brand_name(name):
    """Map a brand name (e.g. ZOLOFT) to the generic name most reported with it."""
    data, error = fetch_openfda({
        "search": f'patient.drug.openfda.brand_name:"{name}"',
        "count": "patient.drug.openfda.generic_name.exact",
        "limit": 1,
    })
    if error:
        return None
    return strip_salt(data["results"][0]["term"])


# Reports name the same molecule several ways (SERTRALINE, SERTRALINE
# HYDROCHLORIDE). The phrase search on "SERTRALINE" matches both, while
# "SERTRALINE HYDROCHLORIDE" would miss half the reports.
SALT_WORDS = {
    "HYDROCHLORIDE", "HCL", "SODIUM", "POTASSIUM", "CALCIUM", "MAGNESIUM",
    "MALEATE", "SUCCINATE", "TARTRATE", "BESYLATE", "MESYLATE", "CITRATE",
    "SULFATE", "PHOSPHATE", "ACETATE", "FUMARATE", "BROMIDE", "OXALATE",
}


def strip_salt(generic):
    words = generic.split()
    while len(words) > 1 and words[-1] in SALT_WORDS:
        words.pop()
    return " ".join(words)


def find_drug(name, catalog):
    """Turn user input into a generic name openFDA knows.

    Returns (generic_name, message). `message` explains a failure, or notes
    a brand-name translation when the drug was found.
    """
    name = name.strip().upper()
    if name == "":
        return None, "Please type a medication name."

    if catalog is not None and name in catalog["drug"].values:
        return name, None

    total, error = count_reports(name)
    if error:
        return None, error
    if total > 0:
        return name, None

    generic = resolve_brand_name(name)
    if generic:
        return generic, f"'{name}' is a brand name, showing its generic: {generic}."

    suggestions = suggest_drug(name, catalog)
    if suggestions:
        return None, f"'{name}' not found. Did you mean: {', '.join(suggestions)}?"
    return None, f"'{name}' was not found in the openFDA database."


# ---------------------------------------------------------------- reactions

def get_top_reactions(drug, limit=10, sex_code=None):
    """Most reported reactions, with the % of the drug's reports that mention each."""
    data, error = fetch_openfda({
        "search": build_search(drug, sex_code),
        "count": "patient.reaction.reactionmeddrapt.exact",
        "limit": limit,
    })
    if error:
        return None, error

    df = pd.DataFrame(data["results"])
    df.columns = ["reaction", "reports"]

    total, error = count_reports(drug, sex_code)
    if error:
        return None, error
    df["percent"] = (df["reports"] / total * 100).round(1)
    return df, None


def get_reports_by_sex(drug):
    data, error = fetch_openfda({
        "search": build_search(drug),
        "count": "patient.patientsex",
    })
    if error:
        return None, error

    df = pd.DataFrame(data["results"])
    df.columns = ["sex_code", "reports"]
    df["sex"] = df["sex_code"].astype(int).map(SEX_LABELS)
    df["percent"] = (df["reports"] / df["reports"].sum() * 100).round(1)
    return df[["sex", "reports", "percent"]], None


def compare_by_sex(drug, top=10, depth=100):
    """Side-by-side % of women's and men's reports mentioning each reaction.

    Takes the union of each sex's top `top` reactions. Percentages are looked
    up in a deeper list (`depth`), so a reaction in the women's top 10 but
    only 14th for men still gets a real number for men instead of a blank.
    """
    women, error = get_top_reactions(drug, limit=depth, sex_code=WOMEN)
    if error:
        return None, error
    men, error = get_top_reactions(drug, limit=depth, sex_code=MEN)
    if error:
        return None, error

    reactions = list(dict.fromkeys(
        women["reaction"].head(top).tolist() + men["reaction"].head(top).tolist()
    ))
    comparison = pd.DataFrame({"reaction": reactions})
    comparison = comparison.merge(
        women[["reaction", "percent"]].rename(columns={"percent": "percent_women"}),
        on="reaction", how="left", validate="one_to_one",
    ).merge(
        men[["reaction", "percent"]].rename(columns={"percent": "percent_men"}),
        on="reaction", how="left", validate="one_to_one",
    )
    comparison["difference"] = (comparison["percent_women"] - comparison["percent_men"]).round(1)
    return comparison.sort_values("percent_women", ascending=False, na_position="last"), None


# ---------------------------------------------------------------- time

# openFDA's FAERS data starts in 2004; the few earlier dates are stray
# records that would draw a misleading flat line at zero.
FIRST_YEAR = 2004


def get_yearly_reports(drug):
    """Reports received per year, 2004 to last year (the current year is incomplete)."""
    data, error = fetch_openfda({
        "search": build_search(drug),
        "count": "receivedate",
    })
    if error:
        return None, error

    df = pd.DataFrame(data["results"])
    df.columns = ["date", "reports"]
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    df["year"] = df["date"].dt.year
    yearly = df.groupby("year")["reports"].sum().reset_index()
    yearly = yearly[(yearly["year"] >= FIRST_YEAR) & (yearly["year"] < date.today().year)]
    return yearly.reset_index(drop=True), None


# ---------------------------------------------------------------- signals

def get_global_reaction_counts():
    """Reports per reaction across the whole database (most common terms only)."""
    data, error = fetch_openfda({
        "count": "patient.reaction.reactionmeddrapt.exact",
        "limit": MAX_COUNT_LIMIT,
    })
    if error:
        return None, error
    return {row["term"]: row["count"] for row in data["results"]}, None


def count_reaction_reports(reaction):
    data, error = fetch_openfda({
        "search": f'patient.reaction.reactionmeddrapt.exact:"{reaction}"',
        "limit": 1,
    })
    if error:
        return None, error
    return data["meta"]["results"]["total"], None


def prr(a, b, c, d):
    """Proportional reporting ratio with a 95% confidence interval.

    a: reports with the drug and the reaction    b: drug, other reactions
    c: other drugs, the reaction                 d: other drugs, other reactions
    """
    if min(a, b, c, d) <= 0:
        return math.nan, math.nan, math.nan
    value = (a / (a + b)) / (c / (c + d))
    se = math.sqrt(1 / a - 1 / (a + b) + 1 / c - 1 / (c + d))
    return value, value * math.exp(-1.96 * se), value * math.exp(1.96 * se)


def get_reaction_signals(drug, limit=50, min_reports=3):
    """Rank a drug's reactions by how over-represented they are versus all other drugs.

    Raw counts are dominated by reactions reported for every drug ("drug
    ineffective", "nausea"). The PRR asks a better question: is this reaction
    a bigger share of this drug's reports than of everyone else's?
    A signal is flagged when PRR >= 2, the CI lower bound is above 1 and
    there are at least `min_reports` reports (a common screening rule).
    """
    reactions, error = get_top_reactions(drug, limit=limit)
    if error:
        return None, error
    drug_total, error = count_reports(drug)
    if error:
        return None, error
    db_total, error = count_reports()
    if error:
        return None, error
    global_counts, error = get_global_reaction_counts()
    if error:
        return None, error

    rows = []
    for _, row in reactions.iterrows():
        reaction_total = global_counts.get(row["reaction"])
        if reaction_total is None:
            reaction_total, error = count_reaction_reports(row["reaction"])
            if error:
                continue

        a = int(row["reports"])
        b = drug_total - a
        c = reaction_total - a
        d = db_total - drug_total - c
        value, low, high = prr(a, b, c, d)
        rows.append({
            "reaction": row["reaction"],
            "reports": a,
            "percent_drug": round(a / drug_total * 100, 2),
            "percent_others": round(c / (c + d) * 100, 2) if c + d > 0 else math.nan,
            "prr": round(value, 2),
            "ci_low": round(low, 2),
            "ci_high": round(high, 2),
        })

    signals = pd.DataFrame(rows)
    signals["signal"] = (
        (signals["prr"] >= 2) & (signals["ci_low"] > 1) & (signals["reports"] >= min_reports)
    )
    return signals.sort_values("prr", ascending=False).reset_index(drop=True), None
