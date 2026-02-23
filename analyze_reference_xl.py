import pandas as pd
import os

file_path = 'Strat Edge-Project Management Tool.xlsx'
xl = pd.ExcelFile(file_path)

print(f"File: {file_path}")
print(f"Sheets: {xl.sheet_names}")

for sheet in xl.sheet_names:
    print(f"\n--- Sheet: {sheet} ---")
    df = pd.read_excel(xl, sheet, header=None, nrows=20)
    print(df)
