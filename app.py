
import os, json
from datetime import datetime
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, ctx
from dash import dash_table
import dash_bootstrap_components as dbc

APP_TITLE = "CSV Pivot Analyzer v8.2 — Retail Pivot (Web)"

DATA_FOLDER = "data"
EXPORT_FOLDER = "exports"
SETTINGS_FILE = "settings.json"
os.makedirs(DATA_FOLDER, exist_ok=True)
os.makedirs(EXPORT_FOLDER, exist_ok=True)

def _safe_read_csv(path):
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(path, low_memory=False, encoding=enc)
        except Exception:
            pass
    return pd.read_csv(path, low_memory=False)

def load_all_csvs():
    files = [f for f in os.listdir(DATA_FOLDER) if f.lower().endswith(".csv")]
    if not files: return pd.DataFrame()
    dfs = []
    for f in files:
        try:
            df = _safe_read_csv(os.path.join(DATA_FOLDER, f))
            df["__source__"] = f
            dfs.append(df)
        except Exception as e:
            print("[WARN] load", f, e)
    if not dfs: return pd.DataFrame()
    df = pd.concat(dfs, ignore_index=True)
    for c in df.columns:
        if df[c].dtype == "object":
            s = df[c].astype(str).str.replace(",", "", regex=False).str.strip()
            as_num = pd.to_numeric(s, errors="ignore")
            if pd.api.types.is_numeric_dtype(as_num):
                df[c] = as_num
            else:
                df[c] = s.replace({"nan": None})
    return df

df_all = load_all_csvs()

def obj_cols():
    return [c for c in df_all.columns if df_all[c].dtype == "object" and c != "__source__"]

def num_cols():
    return [c for c in df_all.columns if pd.api.types.is_numeric_dtype(df_all[c])]

def indian_money(v):
    if v is None or pd.isna(v): return ""
    try:
        s = f"{float(v):.2f}"
        ip, dp = s.split(".")
        if len(ip) > 3:
            ip0 = ip[-3:]
            ip1 = ip[:-3]
            parts = []
            while len(ip1) > 2:
                parts.insert(0, ip1[-2:])
                ip1 = ip1[:-2]
            if ip1: parts.insert(0, ip1)
            ip = ",".join(parts + [ip0])
        return f"{ip}.{dp}"
    except Exception:
        return str(v)

def indian_int(v):
    if v is None or pd.isna(v): return ""
    try:
        return f"{int(round(v)):,}".replace(",", "_").replace("_", ",")
    except Exception:
        return str(v)

def pct0(v):
    if v is None or pd.isna(v): return ""
    try:
        return f"{float(v):.0f}%"
    except Exception:
        return str(v)

external_stylesheets = [dbc.themes.BOOTSTRAP]
app = Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server  # for gunicorn
app.title = APP_TITLE

settings = {}
if os.path.exists(SETTINGS_FILE):
    try: settings = json.load(open(SETTINGS_FILE, "r", encoding="utf-8"))
    except Exception: settings = {}

DIM_DEFAULTS = ["DIVISION","SUB_DIVISION","SECTION","DEPARTMENT","BRAND","ARTICLE","STYLE","SIZE","COLOR"]

layout_left = dbc.Col([
    html.H6("Row Dimensions (multi-select)"),
    dcc.Dropdown(id="row-dims", options=[{"label":c,"value":c} for c in obj_cols()],
                 value=[c for c in DIM_DEFAULTS if c in obj_cols()] or settings.get("row_dims", []),
                 multi=True),
    html.Hr(),
    html.H6("Period Columns (optional)"),
    dbc.Row([
        dbc.Col([html.Small("Year"), dcc.Dropdown(id="col-year", options=[{"label":c,"value":c} for c in obj_cols()], value=settings.get("col_year"))], md=6),
        dbc.Col([html.Small("Period Day"), dcc.Dropdown(id="col-period", options=[{"label":c,"value":c} for c in num_cols()], value=settings.get("col_period"))], md=6),
    ], className="g-2"),
    dbc.Input(id="date-caption", placeholder="Header date caption e.g. 22-09-2025 To 02-10-2025",
              value=settings.get("date_caption",""), className="mt-2"),
    html.Hr(),
    html.H6("Map Measures / Formula Inputs"),
    dbc.Row([
        dbc.Col([html.Small("Opening Qty"), dcc.Dropdown(id="m-open-qty", options=[{"label":c,"value":c} for c in num_cols()], value=settings.get("m_open_qty"))], md=6),
        dbc.Col([html.Small("Net Sale Qty"), dcc.Dropdown(id="m-sale-qty", options=[{"label":c,"value":c} for c in num_cols()], value=settings.get("m_sale_qty"))], md=6),
    ], className="g-2"),
    dbc.Row([
        dbc.Col([html.Small("Net Sale Amt"), dcc.Dropdown(id="m-sale-amt", options=[{"label":c,"value":c} for c in num_cols()], value=settings.get("m_sale_amt"))], md=6),
        dbc.Col([html.Small("Net Margin Amt"), dcc.Dropdown(id="m-margin-amt", options=[{"label":c,"value":c} for c in num_cols()], value=settings.get("m_margin_amt"))], md=6),
    ], className="g-2"),
    dbc.Row([
        dbc.Col([html.Small("Purchase Stock Qty"), dcc.Dropdown(id="m-pur-qty", options=[{"label":c,"value":c} for c in num_cols()], value=settings.get("m_pur_qty"))], md=6),
        dbc.Col([html.Small("Purchase Return Qty"), dcc.Dropdown(id="m-pr-qty", options=[{"label":c,"value":c} for c in num_cols()], value=settings.get("m_pr_qty"))], md=6),
    ], className="g-2"),
    dbc.Row([
        dbc.Col([html.Small("Closing Stock Qty"), dcc.Dropdown(id="m-close-qty", options=[{"label":c,"value":c} for c in num_cols()], value=settings.get("m_close_qty"))], md=6),
        dbc.Col([html.Small("Daily Avg Net Sale Qty"), dcc.Dropdown(id="m-davg-qty", options=[{"label":c,"value":c} for c in num_cols()], value=settings.get("m_davg_qty"))], md=6),
    ], className="g-2"),
    html.Small("Inventory Days Formula"),
    dcc.Dropdown(id="inv-days-formula",
                 options=[
                     {"label":"Use Period Day column","value":"period"},
                     {"label":"Compute: ClosingStockQty / DailyAvgNetSaleQty","value":"computed"}
                 ], value=settings.get("inv_days_formula","period")),
    html.Br(),
    dbc.Button("Generate Pivot", id="gen", color="primary", className="me-2"),
    dbc.Button("Export Excel", id="export", color="success"),
    html.Div(id="export-msg", className="text-success mt-2"),
], md=4)

layout_right = dbc.Col([
    dash_table.DataTable(
        id="pivot-table",
        style_table={"overflowX":"auto"},
        style_header={"whiteSpace":"normal","height":"auto","fontWeight":"bold","textAlign":"center","backgroundColor":"#eef3ff"},
        style_cell={"minWidth":90,"whiteSpace":"normal","fontSize":"13px"},
        page_size=20,
        sort_action="native"
    )
], md=8)

app.layout = dbc.Container([
    html.H3("📑 " + APP_TITLE, className="mt-3 mb-3 text-center"),
    dbc.Alert("Upload CSVs to ./data. Map columns → Generate Pivot. Export Excel available.", color="light"),
    dbc.Row([layout_left, layout_right]),
    dcc.Store(id="pivot-data")
], fluid=True)

def build_metrics(df, mp, inv_days_formula):
    out = {}
    # QY-2: default = sum(Net Sale Qty)
    if mp.get("sale_qty"):
        out["QY-2"] = df[mp["sale_qty"]].sum(min_count=1)
    # Net Margin %
    if mp.get("margin_amt") and mp.get("sale_amt"):
        den = df[mp["sale_amt"]].sum(min_count=1)
        num = df[mp["margin_amt"]].sum(min_count=1)
        out["Sum of Net Margin %"] = (num / den * 100.0) if den not in (0, None, float("nan")) else None
    # Net Sale Amt
    if mp.get("sale_amt"):
        out["Sum of Net Sale Amt"] = df[mp["sale_amt"]].sum(min_count=1)
    # Sell Through %
    if mp.get("sale_qty") and (mp.get("open_qty") or mp.get("pur_qty")):
        den = (df[mp["open_qty"]].sum(min_count=1) if mp.get("open_qty") else 0) + \
              (df[mp["pur_qty"]].sum(min_count=1) if mp.get("pur_qty") else 0) - \
              (df[mp["pr_qty"]].sum(min_count=1) if mp.get("pr_qty") else 0)
        num = df[mp["sale_qty"]].sum(min_count=1)
        out["Sum of Sell Through %"] = (num / den * 100.0) if den not in (0, None, float("nan")) else None
    # Inventory Days
    if inv_days_formula == "period" and mp.get("period"):
        out["Sum of Inventory Days"] = df[mp["period"]].mean()
    elif inv_days_formula == "computed" and mp.get("close_qty") and mp.get("davg_qty"):
        den = df[mp["davg_qty"]].mean()
        num = df[mp["close_qty"]].mean()
        out["Sum of Inventory Days"] = (num / den) if den not in (0, None, float("nan")) else None
    # Net Sale Qty
    if mp.get("sale_qty"):
        out["Sum of Net Sale Qty"] = df[mp["sale_qty"]].sum(min_count=1)
    return out

def indian_money(v):
    if v is None or pd.isna(v): return ""
    try:
        s = f"{float(v):.2f}"
        ip, dp = s.split(".")
        if len(ip) > 3:
            ip0 = ip[-3:]
            ip1 = ip[:-3]
            parts = []
            while len(ip1) > 2:
                parts.insert(0, ip1[-2:])
                ip1 = ip1[:-2]
            if ip1: parts.insert(0, ip1)
            ip = ",".join(parts + [ip0])
        return f"{ip}.{dp}"
    except Exception:
        return str(v)

def indian_int(v):
    if v is None or pd.isna(v): return ""
    try:
        return f"{int(round(v)):,}".replace(",", "_").replace("_", ",")
    except Exception:
        return str(v)

def pct0(v):
    if v is None or pd.isna(v): return ""
    try:
        return f"{float(v):.0f}%"
    except Exception:
        return str(v)

def to_display(df, date_caption):
    columns = []
    for c in df.columns:
        if c == "Row":
            columns.append({"name":["DIVISION2 / Others",""], "id":"Row"})
        else:
            columns.append({"name":[c, date_caption or ""], "id":c})
    data = []
    for _, r in df.iterrows():
        row = {}
        for c, v in r.items():
            if c == "Row": row[c] = v
            elif c in ("Sum of Net Sale Qty",): row[c] = indian_int(v)
            elif c in ("Sum of Net Sale Amt",): row[c] = indian_money(v)
            elif c in ("Sum of Net Margin %","Sum of Sell Through %"): row[c] = pct0(v)
            elif c in ("Sum of Inventory Days",): row[c] = "" if pd.isna(v) else f"{float(v):.0f}"
            elif c == "QY-2": row[c] = str(v) if v is not None else ""
            else: row[c] = v
        data.append(row)
    return columns, data

@app.callback(
    Output("pivot-table","columns"),
    Output("pivot-table","data"),
    Output("pivot-data","data"),
    Input("gen","n_clicks"),
    State("row-dims","value"),
    State("col-year","value"),
    State("col-period","value"),
    State("date-caption","value"),
    State("m-open-qty","value"),
    State("m-sale-qty","value"),
    State("m-sale-amt","value"),
    State("m-margin-amt","value"),
    State("m-pur-qty","value"),
    State("m-pr-qty","value"),
    State("m-close-qty","value"),
    State("m-davg-qty","value"),
    State("inv-days-formula","value"),
    prevent_initial_call=True
)
def generate(n, row_dims, col_year, col_period, date_caption,
             open_qty, sale_qty, sale_amt, margin_amt, pur_qty, pr_qty, close_qty, davg_qty, inv_days_formula):
    if not row_dims: return [], [], None

    # persist small UI state
    payload = {
        "row_dims": row_dims, "col_year": col_year, "col_period": col_period,
        "date_caption": date_caption,
        "m_open_qty": open_qty, "m_sale_qty": sale_qty, "m_sale_amt": sale_amt, "m_margin_amt": margin_amt,
        "m_pur_qty": pur_qty, "m_pr_qty": pr_qty, "m_close_qty": close_qty, "m_davg_qty": davg_qty,
        "inv_days_formula": inv_days_formula
    }
    try: json.dump(payload, open(SETTINGS_FILE,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    except Exception: pass

    df = df_all.copy()
    mp = {
        "year": col_year, "period": col_period,
        "open_qty": open_qty, "sale_qty": sale_qty, "sale_amt": sale_amt, "margin_amt": margin_amt,
        "pur_qty": pur_qty, "pr_qty": pr_qty, "close_qty": close_qty, "davg_qty": davg_qty
    }
    g = df.groupby(row_dims, dropna=False)

    rows = []
    for keys, sub in g:
        if not isinstance(keys, tuple): keys = (keys,)
        row = {"Row": " / ".join("(blank)" if pd.isna(k) else str(k) for k in keys)}
        row.update(build_metrics(sub, mp, inv_days_formula))
        rows.append(row)
    pvt = pd.DataFrame(rows)

    total = {"Row":"Grand Total"}
    total.update(build_metrics(df, mp, inv_days_formula))
    pvt = pd.concat([pvt, pd.DataFrame([total])], ignore_index=True)

    ordered = ["Row","QY-2","Sum of Net Margin %","Sum of Net Sale Amt","Sum of Sell Through %","Sum of Inventory Days","Sum of Net Sale Qty"]
    pvt = pvt[[c for c in ordered if c in pvt.columns]]

    columns, data = to_display(pvt, date_caption)
    return columns, data, {"raw": pvt.to_dict("records")}

@app.callback(
    Output("export-msg","children"),
    Input("export","n_clicks"),
    State("pivot-data","data"),
    prevent_initial_call=True
)
def export_excel(n, pdata):
    if not n: return ""
    if not pdata: return "⚠️ Generate pivot first."
    out = os.path.join(EXPORT_FOLDER, f"pivot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
    try:
        pd.DataFrame(pdata["raw"]).to_excel(out, index=False)
        return f"✅ Exported: {out}"
    except Exception as e:
        return f"❌ Export failed: {e}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
