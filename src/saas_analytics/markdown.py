from __future__ import annotations

import pandas as pd


def dataframe_to_markdown(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    columns = [str(column) for column in frame.columns]
    rows = [[_format(value) for value in row] for row in frame.to_numpy()]
    widths = [max(len(columns[index]), *(len(row[index]) for row in rows)) for index in range(len(columns))]
    header = "| " + " | ".join(column.ljust(widths[index]) for index, column in enumerate(columns)) + " |"
    separator = "| " + " | ".join("-" * width for width in widths) + " |"
    body = ["| " + " | ".join(value.ljust(widths[index]) for index, value in enumerate(row)) + " |" for row in rows]
    return "\n".join([header, separator, *body])


def _format(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value)
