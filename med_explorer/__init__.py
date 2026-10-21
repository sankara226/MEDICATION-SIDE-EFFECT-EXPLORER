"""Medication Side Effect Explorer: FAERS adverse event analysis via openFDA."""

from .analysis import (
    compare_by_sex,
    count_reports,
    find_drug,
    get_drug_catalog,
    get_reaction_signals,
    get_reports_by_sex,
    get_top_reactions,
    get_yearly_reports,
    prr,
    suggest_drug,
)
from .api import fetch_openfda

__version__ = "1.0.0"
