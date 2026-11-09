"""Offline tests: openFDA is replaced by a fake that answers from a dict."""

import math
from datetime import date

import pandas as pd
import pytest
import requests

from med_explorer import analysis, api


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


def counts(*pairs):
    return {"results": [{"term": t, "count": c} for t, c in pairs]}


def total(n):
    return {"meta": {"results": {"total": n}}}


@pytest.fixture
def fake_fda(monkeypatch):
    """Route requests.get through a table of {(search, count): response}."""
    routes = {}
    calls = []

    def fake_get(url, params, timeout):
        calls.append(params)
        key = (params.get("search"), params.get("count"))
        if key not in routes:
            return FakeResponse(404)
        route = routes[key]
        if isinstance(route, Exception):
            raise route
        if isinstance(route, FakeResponse):
            return route
        return FakeResponse(200, route)

    api.clear_cache()
    monkeypatch.setattr(api.requests, "get", fake_get)
    yield routes, calls
    api.clear_cache()


DRUG = 'patient.drug.openfda.generic_name:"SERTRALINE"'
REACTIONS = "patient.reaction.reactionmeddrapt.exact"


# ---------------------------------------------------------------- api

def test_errors_become_messages(fake_fda):
    routes, _ = fake_fda
    routes[("a", None)] = FakeResponse(429)
    routes[("b", None)] = FakeResponse(500)
    routes[("c", None)] = requests.exceptions.Timeout()
    routes[("d", None)] = requests.exceptions.ConnectionError()

    assert "Too many requests" in api.fetch_openfda({"search": "a"})[1]
    assert "code 500" in api.fetch_openfda({"search": "b"})[1]
    assert "too long" in api.fetch_openfda({"search": "c"})[1]
    assert "connect" in api.fetch_openfda({"search": "d"})[1]


@pytest.mark.parametrize("raw", ["abc", " abc ", "abc\n", '"abc"', "'abc' "])
def test_clean_key(raw):
    assert api.clean_key(raw) == "abc"


@pytest.mark.parametrize("raw", [None, "", "   ", '""'])
def test_clean_key_empty(raw):
    assert api.clean_key(raw) is None


def test_rejected_key_falls_back_to_no_key(fake_fda, monkeypatch):
    _, calls = fake_fda
    monkeypatch.setattr(api, "API_KEY", "bad-key")

    def fake_get(url, params, timeout):
        calls.append(params)
        return FakeResponse(403) if "api_key" in params else FakeResponse(200, total(7))

    monkeypatch.setattr(api.requests, "get", fake_get)
    data, error = api.fetch_openfda({"count": "x", "limit": 1000})

    assert error is None and data == total(7)
    assert api.API_KEY is None
    assert calls[-1] == {"count": "x", "limit": 500}


def test_successes_are_cached_but_errors_are_not(fake_fda):
    routes, calls = fake_fda
    routes[("ok", None)] = total(5)
    api.fetch_openfda({"search": "ok"})
    api.fetch_openfda({"search": "ok"})
    api.fetch_openfda({"search": "missing"})
    api.fetch_openfda({"search": "missing"})
    assert len(calls) == 3


# ---------------------------------------------------------------- finding drugs

def test_count_reports_treats_404_as_zero(fake_fda):
    assert analysis.count_reports("NOTADRUG") == (0, None)


def test_count_reports_passes_real_errors_through(fake_fda):
    routes, _ = fake_fda
    routes[(analysis.build_search("X"), None)] = FakeResponse(429)
    result, error = analysis.count_reports("X")
    assert result is None and "Too many requests" in error


def test_build_search_with_sex():
    assert analysis.build_search("SERTRALINE", 2) == DRUG + " AND patient.patientsex:2"


@pytest.mark.parametrize("raw, expected", [
    ("SERTRALINE HYDROCHLORIDE", "SERTRALINE"),
    ("METOPROLOL SUCCINATE", "METOPROLOL"),
    ("ACETAMINOPHEN", "ACETAMINOPHEN"),
    ("SODIUM", "SODIUM"),
])
def test_strip_salt(raw, expected):
    assert analysis.strip_salt(raw) == expected


def test_find_drug_paths(fake_fda):
    routes, _ = fake_fda
    catalog = pd.DataFrame({"drug": ["SERTRALINE", "IBUPROFEN"], "reports": [10, 20]})
    routes[('patient.drug.openfda.brand_name:"ZOLOFT"', "patient.drug.openfda.generic_name.exact")] = \
        counts(("SERTRALINE HYDROCHLORIDE", 99))

    assert analysis.find_drug("  sertraline ", catalog) == ("SERTRALINE", None)
    assert analysis.find_drug("", catalog)[1] == "Please type a medication name."

    name, note = analysis.find_drug("zoloft", catalog)
    assert name == "SERTRALINE" and "brand name" in note

    name, message = analysis.find_drug("ibuprofin", catalog)
    assert name is None and "IBUPROFEN" in message

    name, message = analysis.find_drug("xyzabc", catalog)
    assert name is None and "not found" in message


def test_find_drug_without_catalog(fake_fda):
    name, message = analysis.find_drug("xyzabc", None)
    assert name is None and "not found" in message


# ---------------------------------------------------------------- analysis

def test_top_reactions_percent(fake_fda):
    routes, _ = fake_fda
    routes[(DRUG, REACTIONS)] = counts(("NAUSEA", 50), ("HEADACHE", 25))
    routes[(DRUG, None)] = total(200)

    df, error = analysis.get_top_reactions("SERTRALINE")
    assert error is None
    assert df["percent"].tolist() == [25.0, 12.5]


def test_reports_by_sex_labels(fake_fda):
    routes, _ = fake_fda
    routes[(DRUG, "patient.patientsex")] = counts((2, 60), (1, 39), (0, 1))
    df, _ = analysis.get_reports_by_sex("SERTRALINE")
    assert df["sex"].tolist() == ["Female", "Male", "Unknown"]
    assert df["percent"].tolist() == [60.0, 39.0, 1.0]


def test_compare_by_sex_fills_from_deeper_list(fake_fda):
    routes, _ = fake_fda
    women, men = analysis.build_search("SERTRALINE", 2), analysis.build_search("SERTRALINE", 1)
    routes[(women, REACTIONS)] = counts(("NAUSEA", 30), ("HEADACHE", 20), ("TREMOR", 1))
    routes[(men, REACTIONS)] = counts(("TREMOR", 10), ("NAUSEA", 5), ("HEADACHE", 1))
    routes[(women, None)] = total(100)
    routes[(men, None)] = total(50)

    comparison, _ = analysis.compare_by_sex("SERTRALINE", top=1, depth=3)
    row = comparison.set_index("reaction").loc["TREMOR"]
    assert set(comparison["reaction"]) == {"NAUSEA", "TREMOR"}
    assert row["percent_women"] == 1.0 and row["percent_men"] == 20.0
    assert row["difference"] == -19.0


def test_yearly_drops_stray_early_dates_and_current_year(fake_fda):
    routes, _ = fake_fda
    this_year = date.today().year
    routes[(DRUG, "receivedate")] = {"results": [
        {"time": "19970620", "count": 1},
        {"time": "20200105", "count": 3},
        {"time": "20200610", "count": 4},
        {"time": "20210101", "count": 5},
        {"time": f"{this_year}0101", "count": 9},
    ]}
    yearly, _ = analysis.get_yearly_reports("SERTRALINE")
    assert yearly["year"].tolist() == [2020, 2021]
    assert yearly["reports"].tolist() == [7, 5]


def test_errors_propagate_instead_of_crashing(fake_fda):
    for function in (analysis.get_top_reactions, analysis.get_reports_by_sex,
                     analysis.get_yearly_reports, analysis.get_reaction_signals):
        result, error = function("NOTADRUG")
        assert result is None and error


# ---------------------------------------------------------------- signals

def test_prr_known_values():
    # 20/100 of the drug's reports vs 100/10,000 for other drugs: 20% / 1% = 20
    value, low, high = analysis.prr(20, 80, 100, 9900)
    assert value == pytest.approx(20.0)
    assert low < value < high


def test_prr_with_empty_cell_is_nan():
    assert all(math.isnan(x) for x in analysis.prr(0, 10, 5, 100))


def test_reaction_signals(fake_fda):
    routes, _ = fake_fda
    routes[(DRUG, REACTIONS)] = counts(("TREMOR", 50), ("NAUSEA", 100), ("RARE THING", 2))
    routes[(DRUG, None)] = total(1_000)
    routes[(None, None)] = total(100_000)
    routes[(None, REACTIONS)] = counts(("NAUSEA", 10_000), ("TREMOR", 500))
    routes[('patient.reaction.reactionmeddrapt.exact:"RARE THING"', None)] = total(4)

    signals, error = analysis.get_reaction_signals("SERTRALINE")
    assert error is None
    by_reaction = signals.set_index("reaction")

    assert by_reaction.loc["TREMOR", "signal"]                # 5% vs ~0.45%
    assert not by_reaction.loc["NAUSEA", "signal"]            # 10% vs ~10%
    assert not by_reaction.loc["RARE THING", "signal"]        # too few reports
    assert signals.iloc[0]["reaction"] == "RARE THING"        # sorted by PRR
