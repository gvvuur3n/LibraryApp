import streamlit as st
import pandas as pd
import json
from pathlib import Path
from io import BytesIO

# PDF dependencies
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

import gspread
from google.oauth2 import service_account

# --- Google Sheets Setup ---
SHEET_NAME = "Boeken_Map"
SPREADSHEET_ID = "1RqKZ9Ge8qR0tpE77C3whCDhARkheVrwBQ96CHmLtqeY"  # <-- from the Google Sheets URL

@st.cache_data(ttl=60)
def load_sheet():
    """Load data from Google Sheets into a DataFrame."""
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    client = gspread.authorize(credentials)
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    return df

def save_to_sheet(df):
    """Save the DataFrame back to Google Sheets and refresh cache."""
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    client = gspread.authorize(credentials)
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
    
    # clear existing content
    sheet.clear()
    # update with new data
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

    load_sheet.clear()  # ✅ clear cache right here
    st.success("✅ Gegevens opgeslagen in Google Sheets!")

# -------------- CONFIGURATION --------------
st.set_page_config(page_title="📚 Boekenbeheer", layout="wide")

FILE_DEFAULT = Path("Boeken_Map.xlsx")
SETTINGS_FILE = Path("settings.json")

# -------------- DATA HANDLING --------------
@st.cache_data
def load_excel():
    try:
        df = pd.read_excel(FILE_DEFAULT, sheet_name="Boeken lijst")
    except Exception as e:
        st.error(f"❌ Fout bij het laden van gegevens: {e}")
        st.stop()
    return df

def save_excel(df):
    """Save updated data back to Excel, clean text, and clear Streamlit cache."""
    df = df.apply(lambda x: x.str.strip().replace(r"\s+", " ", regex=True))
    for c in df.columns:
        if "locatie" in c:
            df[c] = df[c].str.capitalize()
        if "taal" in c:
            df[c] = df[c].str.capitalize()
        if "categorie" in c:
            df[c] = df[c].str.capitalize()
        if "titel" in c or "schrijver" in c or "auteur" in c:
            df[c] = df[c].str.strip().str.replace(r"\s+", " ", regex=True)

    sheets = pd.read_excel(FILE_DEFAULT, sheet_name=None)
    sheets["Boeken lijst"] = df
    with pd.ExcelWriter(FILE_DEFAULT, engine="openpyxl") as writer:
        for name, data in sheets.items():
            data.to_excel(writer, sheet_name=name, index=False)

    load_sheet.clear()
    st.success("✅ Gegevens succesvol opgeslagen!")
    st.rerun()

def delete_book(df, index):
    """Delete a book at the given index and update Excel."""
    df = df.drop(index)
    df.reset_index(drop=True, inplace=True)
    save_to_sheet(df)
    st.success("🗑️ Boek verwijderd!")
    st.rerun()

def generate_pdf_table(dataframe, title):
    """Generate a clean, formatted PDF from a dataframe."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    elements = []
    styles = getSampleStyleSheet()

    # Title
    title_paragraph = Paragraph(f"<b>Boekenlijst — {title}</b>", styles["Title"])
    elements.append(title_paragraph)
    elements.append(Spacer(1, 0.4 * cm))

    data = [list(dataframe.columns)] + dataframe.values.tolist()

    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F81BD")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ]
        )
    )

    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer


# -------------- LOAD DATA --------------
df = load_sheet()

# Clean columns
df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
df.columns = df.columns.str.strip().str.lower()
df = df.astype(str)

# Identify column names
col_map = {}
for c in df.columns:
    if "taal" in c:
        col_map["taal"] = c
    if "locatie" in c:
        col_map["locatie"] = c
    if "titel" in c:
        col_map["titel"] = c
    if "schrijver" in c or "auteur" in c:
        col_map["schrijver"] = c
    if "categorie" in c:
        col_map["categorie"] = c


# -------------- SIDEBAR NAVIGATION --------------
st.sidebar.title("📖 Boekenbeheer")
page = st.sidebar.radio("Menu", ["🔍 Zoek / Filter / Bewerk", "➕ Nieuw boek"])

st.title("📘 Boeken Lijst")


# ============================================================
# 🔍 PAGE 1 — SEARCH / FILTER / EDIT + PDF Export
# ============================================================
if page == "🔍 Zoek / Filter / Bewerk":
    st.subheader("Zoek, filter, bewerk of exporteer boeken")

    # Quick Stats
    total_books = len(df)
    unique_lang = df[col_map["taal"]].nunique() if "taal" in col_map else 0
    unique_cats = df[col_map["categorie"]].nunique() if "categorie" in col_map else 0
    unique_locs = df[col_map["locatie"]].nunique() if "locatie" in col_map else 0

    colA, colB, colC, colD = st.columns(4)
    colA.metric("📚 Boeken totaal", total_books)
    colB.metric("🌐 Talen", unique_lang)
    colC.metric("🏷️ Categorieën", unique_cats)
    colD.metric("📍 Locaties", unique_locs)

    st.divider()

    # Search & Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        query = st.text_input("🔍 Zoek op titel of schrijver:")
    with col2:
        genre_col = col_map.get("categorie")
        genre_opts = ["Alle"] + sorted(df[genre_col].dropna().unique().tolist()) if genre_col else []
        genre_filter = st.selectbox("🏷️ Filter op categorie:", genre_opts) if genre_opts else None
    with col3:
        loc_col = col_map.get("locatie")
        loc_opts = ["Alle"] + sorted(df[loc_col].dropna().unique().tolist()) if loc_col else []
        locatie_filter = st.selectbox("📍 Filter op locatie:", loc_opts) if loc_opts else None

    # Apply filters
    results = df.copy()
    if query:
        query = query.strip()
        mask = results.apply(lambda r: r.astype(str).str.contains(query, case=False, na=False, regex=False)).any(axis=1)
        results = results[mask]
    if genre_filter and genre_filter != "Alle":
        results = results[results[genre_col] == genre_filter]
    if locatie_filter and locatie_filter != "Alle":
        results = results[results[loc_col] == locatie_filter]

    st.write("### 📋 Zoekresultaten")
    st.caption("Vink een boek aan om te bewerken")

    # --- PDF Export of filtered data ---
    if not results.empty:
        pdf_file = generate_pdf_table(results, "Huidige selectie")
        st.download_button(
            label="📄 Exporteer huidige resultaten naar PDF",
            data=pdf_file,
            file_name="Boekenlijst_filtered.pdf",
            mime="application/pdf",
        )

    # Display results + editing
    if results.empty:
        st.warning("Geen resultaten gevonden. Pas je filters aan.")
    else:
        results_display = results.copy()
        results_display.insert(0, "Selecteer", False)

        selected_table = st.data_editor(
            results_display,
            width="stretch",
            height=400,
            key="select_table",
            use_container_width=False,
            hide_index=False,
        )

        selected_rows = selected_table[selected_table["Selecteer"] == True]

        if not selected_rows.empty:
            selected_row = selected_rows.iloc[0]
            titel_col = col_map.get("titel", "titel")
            match_idx = df[df[titel_col] == selected_row[titel_col]].index

            if not match_idx.empty:
                idx = match_idx[0]
                row = df.loc[idx].copy()

                st.divider()
                st.write("✏️ **Bewerk geselecteerd boek:**")

                edited = {}
                for col in df.columns:
                    label = col.capitalize()
                    if col == col_map.get("taal"):
                        opts = sorted(df[col].dropna().unique().tolist())
                        edited[col] = st.selectbox(f"🌐 {label}", opts, index=opts.index(df.at[idx, col]) if df.at[idx, col] in opts else 0)
                    elif col == col_map.get("categorie"):
                        opts = sorted(df[col].dropna().unique().tolist())
                        edited[col] = st.selectbox(f"🏷️ {label}", opts, index=opts.index(df.at[idx, col]) if df.at[idx, col] in opts else 0)
                    elif col == col_map.get("locatie"):
                        opts = sorted(df[col].dropna().unique().tolist())
                        edited[col] = st.selectbox(f"📍 {label}", opts, index=opts.index(df.at[idx, col]) if df.at[idx, col] in opts else 0)
                    else:
                        edited[col] = st.text_input(label, str(df.at[idx, col]) if not pd.isna(df.at[idx, col]) else "")

                col_a, col_b = st.columns(2)

                with col_a:
                    if st.button("💾 Opslaan wijzigingen"):
                        for col in df.columns:
                            df.at[idx, col] = edited[col]
                        save_to_sheet(df)
                        st.success(f"✅ Boek '{df.at[idx, titel_col]}' is opgeslagen!")
                        st.rerun()

                with col_b:
                    st.markdown("#### 🗑️ Verwijderen")
                    confirm = st.checkbox("Bevestig verwijdering", key=f"confirm_delete_{idx}")
                    if st.button("❌ Verwijder boek permanent"):
                        if confirm:
                            delete_book(df, idx)
                        else:
                            st.warning("⚠️ Vink de bevestiging aan om te verwijderen.")


# ============================================================
# ➕ PAGE 2 — ADD NEW BOOK (fields reset after submit)
# ============================================================
elif page == "➕ Nieuw boek":
    st.subheader("Nieuw boek toevoegen")

    taal_col = col_map.get("taal")
    genre_col = col_map.get("categorie")
    locatie_col = col_map.get("locatie")

    taal_opts = sorted(df[taal_col].dropna().unique().tolist()) if taal_col else []
    genre_opts = sorted(df[genre_col].dropna().unique().tolist()) if genre_col else []
    locatie_opts = sorted(df[locatie_col].dropna().unique().tolist()) if locatie_col else []

    # Use a form to isolate the inputs
    with st.form("add_book_form", clear_on_submit=True):
        new_entry = {}

        for col in df.columns:
            col_lower = col.lower()

            if taal_col and col_lower == taal_col:
                use_new_taal = st.checkbox("➕ Nieuwe taal toevoegen?")
                new_entry[col] = (
                    st.text_input("🌐 Nieuwe taal:") if use_new_taal else st.selectbox("🌐 Kies taal:", taal_opts)
                )

            elif genre_col and col_lower == genre_col:
                use_new_genre = st.checkbox("➕ Nieuwe categorie toevoegen?")
                new_entry[col] = (
                    st.text_input("🏷️ Nieuwe categorie:") if use_new_genre else st.selectbox("🏷️ Kies categorie:", genre_opts)
                )

            elif locatie_col and col_lower == locatie_col:
                use_new_loc = st.checkbox("➕ Nieuwe locatie toevoegen?")
                new_entry[col] = (
                    st.text_input("📍 Nieuwe locatie:") if use_new_loc else st.selectbox("📍 Kies locatie:", locatie_opts)
                )

            else:
                new_entry[col] = st.text_input(col.capitalize())

        titel_col = col_map.get("titel", "titel")
        if titel_col in df.columns and new_entry.get(titel_col):
            title_matches = df[df[titel_col].str.lower() == new_entry[titel_col].lower()]
            if not title_matches.empty:
                st.warning("⚠️ Er bestaan al boeken met een vergelijkbare titel:")
                st.dataframe(title_matches, width="stretch")

        # --- Submit button inside the form ---
        submitted = st.form_submit_button("📚 Toevoegen aan lijst")

    # --- Handle submission after form closes ---
    if submitted:
        if titel_col in df.columns and new_entry.get(titel_col):
            title_matches = df[df[titel_col].str.lower() == new_entry[titel_col].lower()]
            if not title_matches.empty:
                st.warning("⚠️ Dubbele titel gevonden. Controleer eerst of het niet al bestaat.")
                st.stop()

        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        save_to_sheet(df)
        st.success("✅ Nieuw boek toegevoegd!")


st.divider()
st.caption("© 2025 Boekenbeheer App — gemaakt voor oma ❤️")
