"""CSV/Excel parsing helpers shared by the upload view."""
import pandas as pd

EMAIL_HEADER_HINTS = ("email", "e-mail", "email address", "recipient")


def parse_tabular_file(django_file):
    """
    Parse an uploaded CSV or Excel file into (columns, records, detected_email_column).

    - columns: list[str] of normalized (trimmed) headers, in original order.
    - records: list[dict] one dict per row, keyed by the normalized headers.
    - detected_email_column: best-guess column name containing email addresses, or "".
    """
    name = (django_file.name or "").lower()
    django_file.seek(0)

    if name.endswith(".csv"):
        df = pd.read_csv(django_file, dtype=str, keep_default_na=False)
    elif name.endswith(".xlsx") or name.endswith(".xls"):
        df = pd.read_excel(django_file, dtype=str)
        df = df.fillna("")
    else:
        raise ValueError("Unsupported file type. Please upload a .csv or .xlsx file.")

    df.columns = [str(c).strip() for c in df.columns]
    columns = list(df.columns)
    records = df.to_dict(orient="records")

    detected_email_column = ""
    for col in columns:
        if col.strip().lower() in EMAIL_HEADER_HINTS:
            detected_email_column = col
            break

    return columns, records, detected_email_column
