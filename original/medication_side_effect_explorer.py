"""
Medication Side-Effect Explorer
Data: openFDA drug adverse event API (FAERS). Educational use only, not medical advice.

SETUP (once, in the VS Code terminal):
    pip install requests pandas matplotlib gradio

HOW TO RUN:
  - Cell by cell: click "Run Cell" above each "# %%" line
    (needs the Python + Jupyter extensions, and: pip install ipykernel)
  - Whole file: python medication_side_effect_explorer.py
    (the exploration charts open one by one; close each window to continue,
     then the Gradio app starts and prints a local link)
"""

# %%
# STEP 1: IMPORT LIBRARIES
import difflib
from datetime import date

import requests
import pandas as pd
import matplotlib.pyplot as plt

# display() is built into Colab/Jupyter. In VS Code we import it so the file
# works both in the Interactive Window and as a plain script.
try:
    from IPython.display import display
except ImportError:
    display = print


# %%
# STEP 2: MAKING FIRST REQUEST TO OPENFDA
drug = "IBUPROFEN"
url = "https://api.fda.gov/drug/event.json"

params = {
    "search": f'patient.drug.openfda.generic_name:"{drug}"',
    "count": "patient.reaction.reactionmeddrapt.exact",
    "limit": 10
}

response = requests.get(url, params=params)
print(f"Status Code: {response.status_code}")


# %%
# STEP 3: API CALL RESPONSE
data = response.json()

print(data.keys())
print(data["results"][:3])


# %%
# STEP 4: DATAFRAME CREATION
df = pd.DataFrame(data["results"])
df.columns = ["reaction", "reports"]
display(df)


# %%
# STEP 5: DOWNLOADING THE DRUG CATALOG
def get_drug_catalog(limit=500):
  url = "https://api.fda.gov/drug/event.json"
  params = {
      "count": "patient.drug.openfda.generic_name.exact",
      "limit": limit
  }
  response = requests.get(url, params=params)
  data = response.json()

  if "results" not in data:
    print("Could not load the catalog:", data.get("error", data))
    return None

  catalog = pd.DataFrame(data["results"])
  catalog.columns = ["drug", "reports"]
  return catalog

catalog = get_drug_catalog()
print(len(catalog), "drugs in catalog")
display(catalog.head(20))


# %%
# STEP 6: CATALOG SEARCH
display(catalog[catalog["drug"].str.contains("pril", case=False)])


# %%
# STEP 7: SUGGESTION FUNCTION
def suggest_drug(name, catalog):
  all_names = catalog["drug"].tolist()
  return difflib.get_close_matches(name.upper(), all_names, n=5, cutoff=0.6)

print(suggest_drug("ibuprofin", catalog))


# %%
# STEP 8: DRUG SEARCH FUNCTION
def find_drug(name, catalog):
  name = name.strip().upper()

  if name in catalog["drug"].values:
    return name

  suggestions = suggest_drug(name, catalog)
  if suggestions:
    print(f"'{name}' not found. Did you mean {', '.join(suggestions)}?")
  else:
    print(f"'{name}' not found, and no similar name in the catalog.")
  return None


# %%
# STEP 9: FUNCTION WRAPPING
def get_top_reactions(drug, limit=10):
    url = "https://api.fda.gov/drug/event.json"
    params = {
        "search": f'patient.drug.openfda.generic_name:"{drug}"',
        "count": "patient.reaction.reactionmeddrapt.exact",
        "limit": limit
    }
    response = requests.get(url, params=params)
    data = response.json()

    # If the FDA sends back an error instead of results, say it clearly
    if "results" not in data:
        print(f"No results for '{drug}':", data.get("error", data))
        return None

    df = pd.DataFrame(data["results"])
    df.columns = ["reaction", "reports"]
    return df

display(get_top_reactions("metformin"))
display(get_top_reactions("sertraline", limit=20))


# %%
# STEP 9b: FUNCTION TEST
df = get_top_reactions("sertraline")

df_sorted = df.sort_values("reports", ascending=True)

plt.figure(figsize=(10,5))
plt.barh(df_sorted["reaction"], df_sorted["reports"], color="teal")
plt.xlabel("Number of reports")
plt.title("Most reported reactions: sertraline")
plt.tight_layout()
plt.show()


# %%
# STEP 10: VISUALIZATION FUNCTION
def visualize_reactions(drug, limit=10):
  df = get_top_reactions(drug, limit)
  df_sorted = df.sort_values("reports", ascending=True)

  plt.figure(figsize=(10,5))
  plt.barh(df_sorted["reaction"], df_sorted["reports"], color="teal")
  plt.xlabel("Number of reports")
  plt.title(f"Most reported reactions: {drug.lower()}")
  plt.tight_layout()
  plt.show()


# %%
# STEP 11: TEST DRUG SEARCH FUNCTION
drug = find_drug("BUPROPION", catalog)

if drug:
  display(get_top_reactions(drug))
  visualize_reactions(drug)


# %%
# STEP 12: COMPARING MEN AND WOMEN REPORTS
def get_reports_by_sex(drug):
  url = "https://api.fda.gov/drug/event.json"
  params = {
      "search": f'patient.drug.openfda.generic_name:"{drug}"',
      "count": "patient.patientsex"
  }
  response = requests.get(url, params=params)
  data = response.json()

  df = pd.DataFrame(data["results"])
  df.columns = ["sex_code", "reports"]

  sex_labels = {0: "Unknown", 1:"Male", 2:"Female"}
  df["sex"] = df["sex_code"].astype(int).map(sex_labels)
  df["percent"] = (df["reports"]/df["reports"].sum() * 100).round(1)

  return df[["sex", "reports", "percent"]]

drug = find_drug("sertraline", catalog)
display(get_reports_by_sex(drug))


# %%
# STEP 13: TOTAL REPORTS FOR ONE SEX
def count_reports(drug, sex_code):
  url = "https://api.fda.gov/drug/event.json"
  params = {
      "search": f'patient.drug.openfda.generic_name:"{drug}" AND patient.patientsex:{sex_code}',
      "limit": 1
  }
  response = requests.get(url, params=params)
  data = response.json()
  return data["meta"]["results"]["total"]

print(f"Women: {count_reports(drug, 2)}")
print(f"Men: {count_reports(drug, 1)}")


# %%
# STEP 14: TOP REACTIONS FOR ONE SEX
def get_reactions_for_sex(drug, sex_code, limit=10):
  url = "https://api.fda.gov/drug/event.json"
  params = {
    "search": f'patient.drug.openfda.generic_name:"{drug}" AND patient.patientsex:{sex_code}',
    "count": "patient.reaction.reactionmeddrapt.exact",
    "limit": limit
  }
  response = requests.get(url, params=params)
  data = response.json()

  df = pd.DataFrame(data["results"])
  df.columns = ["reaction", "reports"]

  total = count_reports(drug, sex_code)
  df["percent"] = (df["reports"] / total * 100).round(1)
  return df

display(get_reactions_for_sex(drug, 2))


# %%
# STEP 15: COMPARE MEN AND WOMEN
women = get_reactions_for_sex(drug, 2)
men = get_reactions_for_sex(drug, 1)

comparison = pd.merge(
    women[["reaction", "percent"]],
    men[["reaction", "percent"]],
    on="reaction",
    how="outer",
    suffixes=("_women", "_men")
)

display(comparison)


# %%
# STEP 16: COMPARISON CHART
comparison.set_index("reaction")[["percent_women", "percent_men"]].plot.barh(
    figsize=(10,5),
    color=["teal", "orange"]
)
plt.xlabel("% of reports mentioning this reaction")
plt.title(f"Reported reactions by sex: {drug.lower()}")
plt.tight_layout()
plt.show()


# %%
# STEP 17: TRENDS OVER TIME
def get_reports_over_time(drug):
  url = "https://api.fda.gov/drug/event.json"
  params = {
      "search": f'patient.drug.openfda.generic_name:"{drug}"',
      "count": "receivedate"
  }
  response = requests.get(url, params=params)
  data = response.json()

  # If the FDA sends back an error instead of results, say it clearly
  if "results" not in data:
    print(f"No results for '{drug}':", data.get("error", data))
    return None

  df = pd.DataFrame(data["results"])
  df.columns = ["date", "reports"]
  df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
  return df

daily = get_reports_over_time(drug)
display(daily.head())


# %%
# STEP 18: GROUPING BY YEAR
def get_yearly_reports(drug):
  daily = get_reports_over_time(drug)
  daily["year"] = daily["date"].dt.year

  yearly = daily.groupby("year")["reports"].sum().reset_index()

  current_year = date.today().year
  yearly = yearly[yearly["year"] < current_year]   # FIX: was "yealy" (typo), so the filter was never applied
  return yearly

yearly = get_yearly_reports(drug)
display(yearly)


# %%
# STEP 19: DRAWING THE TREND
plt.figure(figsize=(10,5))
plt.plot(yearly["year"], yearly["reports"], marker="o", color="teal")
plt.xlabel("Year")
plt.ylabel("Number of reports")
plt.title(f"Reports per year: {drug.lower()}")
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()


# %%
# STEP 20: FIND THE PEAK YEAR
peak = yearly.loc[yearly["reports"].idxmax()]
print(f"Peak year: {int(peak['year'])} with {int(peak['reports'])} reports")


# %%
# STEP 21: COMPARING SEVERAL DRUGS
drugs_to_compare = ["SERTRALINE", "FLUOXETINE", "ESCITALOPRAM"]

plt.figure(figsize=(10,5))

for name in drugs_to_compare:
  yearly = get_yearly_reports(name)
  plt.plot(yearly["year"], yearly["reports"], marker="o", label=name.lower())

plt.xlabel("Year")
plt.ylabel("Number of reports")
plt.title("Reports per year: comparison")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()


# %%
# STEP 22: CATCHING ERRORS
BASE_URL = "https://api.fda.gov/drug/event.json"

def fetch_openfda(params):
  try:
    response = requests.get(BASE_URL, params=params, timeout=15)
  except requests.exceptions.Timeout:   # FIX: was "exceptons"
    return None, "openFDA took too long to answer. Please try again."
  except requests.exceptions.ConnectionError:
    return None, "Could not connect to openFDA. Check your internet connection."

  if response.status_code == 200:
    return response.json(), None
  elif response.status_code == 404:
    return None, "No reports found for this search."
  elif response.status_code == 429:
    return None, "Too many requests right now. Wait a minute and try again."
  else:
    return None, f"Unexpected error from openFDA (code {response.status_code})"


# %%
# STEP 23: REBUILDING THE ANALYSIS FUNCTIONS
# FIX: removed the stray "from IPython.core import error" (auto-import added by Colab)

def build_search(drug, sex_code=None):
    search = f'patient.drug.openfda.generic_name:"{drug}"'
    if sex_code is not None:
        search += f" AND patient.patientsex:{sex_code}"
    return search


def count_reports(drug, sex_code=None):
    data, error = fetch_openfda({"search": build_search(drug, sex_code), "limit": 1})
    if error:
        return 0
    return data["meta"]["results"]["total"]


def get_top_reactions(drug, limit=10, sex_code=None):
  data, error = fetch_openfda({
      "search": build_search(drug, sex_code),
      "count": "patient.reaction.reactionmeddrapt.exact",
      "limit": limit
  })
  if error:
    return None, error

  df = pd.DataFrame(data["results"])
  df.columns = ["reaction", "reports"]
  total = count_reports(drug, sex_code)
  df["percent"] = (df["reports"] / total * 100).round(1)
  return df, None


def get_reports_by_sex(drug):
  data, error = fetch_openfda({
      "search": build_search(drug),
      "count": "patient.patientsex"
  })
  if error:
    return None, error

  df = pd.DataFrame(data["results"])
  df.columns = ["sex_code", "reports"]
  sex_labels = {0: "Unknown", 1:"Male", 2:"Female"}
  df["sex"] = df["sex_code"].astype(int).map(sex_labels)
  df["percent"] = (df["reports"]/df["reports"].sum() * 100).round(1)
  return df[["sex", "reports", "percent"]], None


def get_yearly_reports(drug):
  data, error = fetch_openfda({
      "search": build_search(drug),
      "count": "receivedate"
  })
  if error:
    return None, error

  # FIX: these lines were indented one level too far (inside the "if"), so they never ran
  df = pd.DataFrame(data["results"])
  df.columns = ["date", "reports"]                     # FIX: was "data"
  df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
  df["year"] = df["date"].dt.year
  yearly = df.groupby("year")["reports"].sum().reset_index()   # FIX: was [reports] without quotes
  yearly = yearly[yearly["year"] < date.today().year]
  return yearly, None


# %%
# STEP 24: CLEAN FUNCTION
def find_drug(name, catalog):
  name = name.strip().upper()
  if name == "":
    return None, "Please type a medication name."

  if name in catalog["drug"].values:
    return name, None

  if count_reports(name) > 0:
    return name, None

  suggestions = suggest_drug(name, catalog)
  if suggestions:
    return None, f"'{name}' not found. Did you mean: {', '.join(suggestions)}?"
  return None, f"'{name}' was not found in the openFDA database."


# %%
# STEP 25: TESTING
tests = ["sertraline", " Metformin ", "ibuprofin", "", "xyzabc"]

for t in tests:
    name, message = find_drug(t, catalog)
    if message:
        print(f"'{t}', {message}")
        continue
    df, error = get_top_reactions(name, limit=3)
    if error:
        print(f"'{t}', {error}")
    else:
        print(f"'{t}', OK, top reaction: {df.iloc[0]['reaction']}")


# %%
# STEP 26: CHART FUNCTIONS
# (In Colab this cell started with: !pip install -q gradio)
# In VS Code, install it once in the terminal instead: pip install gradio

def make_reactions_chart(df, drug):
  df_sorted = df.sort_values("reports")   # FIX: was "df_sorrted"
  fig, ax = plt.subplots(figsize=(10,5))
  ax.barh(df_sorted["reaction"], df_sorted["reports"], color="teal")
  ax.set_xlabel("Number of reports")
  ax.set_title(f"Most reported reactions: {drug.lower()}")
  fig.tight_layout()
  plt.close(fig)
  return fig

def make_sex_chart(drug):
  women, error_w = get_top_reactions(drug, sex_code=2)
  men, error_m = get_top_reactions(drug, sex_code=1)
  if error_w or error_m:
    return None

  comparison = pd.merge(
      women[["reaction", "percent"]],
      men[["reaction", "percent"]],
      on="reaction",
      how="outer",
      suffixes=("_women", "_men")
  )
  fig, ax = plt.subplots(figsize=(10,5))
  comparison.set_index("reaction")[["percent_women", "percent_men"]].plot.barh(
      ax=ax, color=["teal", "orange"]
  )
  ax.set_xlabel("% of reports mentioning this reaction")
  ax.set_title(f"Reported reactions by sex: {drug.lower()}")
  fig.tight_layout()
  plt.close(fig)
  return fig

def make_trend_chart(yearly, drug):
  if yearly is None or len(yearly) == 0:
    return None

  fig, ax = plt.subplots(figsize=(10,5))
  ax.plot(yearly["year"], yearly["reports"], marker="o", color="teal")   # FIX: was yearly["yearly"]
  ax.set_xlabel("Year")
  ax.set_ylabel("Number of reports")
  ax.set_title(f"Reports per year: {drug.lower()}")
  ax.grid(alpha=0.3)   # FIX: was "alpa"
  fig.tight_layout()
  plt.close(fig)
  return fig


# %%
# STEP 27: APP FUNCTION
def analyze(drug_input):
  drug, message = find_drug(drug_input, catalog)
  if message:
    return f"{message}", None, None, None, None

  reactions, error = get_top_reactions(drug)
  if error:
    return f"{error}", None, None, None, None

  yearly, _ = get_yearly_reports(drug)
  by_sex, _ = get_reports_by_sex(drug)
  total = count_reports(drug)

  lines = [f"## {drug.title()}", f"**Total reports:** {total:,}"]
  if yearly is not None and len(yearly) > 0:
    peak = yearly.loc[yearly["reports"].idxmax()]
    lines.append(f"**Peak year:** {int(peak['year'])} ({int(peak['reports']):,} reports)")

  if by_sex is not None:
    for _, row in by_sex.iterrows():
      lines.append(f"**{row['sex']}:** {row['percent']}% of reports")

  summary = "\n\n".join(lines)

  return (
    summary,
    reactions,
    make_reactions_chart(reactions, drug),
    make_sex_chart(drug),
    make_trend_chart(yearly, drug)
  )


# %%
# STEP 28: THE GRADIO APP
import gradio as gr

DISCLAIMER = """
---
**About this data:** reports come from the FDA Adverse Event Reporting System (FAERS) via openFDA.
A report means someone took a medication and later experienced a reaction. **It does not prove the medication caused it.**
Report numbers also depend on how widely a drug is used and on media attention.

**This tool is for educational purposes and is not medical advice.**
Never stop or change a medication without talking to your doctor or pharmacist.
"""

with gr.Blocks(title="Medication Side Effect Explorer") as app:
  gr.Markdown("# Medication Side Effect Explorer")
  gr.Markdown("Explore side effects reported to the U.S. FDA for any medication.")

  with gr.Row():
    drug_box = gr.Textbox(label="Medication name", placeholder="e.g. sertraline")
    analyze_btn = gr.Button("Analyze", variant="primary")

  gr.Examples(examples=["sertraline", "metformin", "ibuprofen"], inputs=drug_box)

  summary_out = gr.Markdown()

  with gr.Tabs():
    with gr.Tab("Top reactions"):
      reactions_chart = gr.Plot()
      reactions_table = gr.DataFrame()
    with gr.Tab("Women vs Men"):
      sex_chart = gr.Plot()
    with gr.Tab("Trend over time"):
      trend_chart = gr.Plot()

  gr.Markdown(DISCLAIMER)

  outputs = [summary_out, reactions_table, reactions_chart, sex_chart, trend_chart]
  analyze_btn.click(analyze, inputs=drug_box, outputs=outputs)
  drug_box.submit(analyze, inputs=drug_box, outputs=outputs)

if __name__ == "__main__" or "ipykernel" in __import__("sys").modules:
  app.launch(share=True, debug=True)