import pandas as pd
import streamlit as st
from data import parameters


def remove_duplicates(entries: pd.DataFrame):
    entries = entries.fillna({'Task': '', 'Description': ''})
    
    unique_entries = entries.groupby(
        ['Project', 'Task', 'Description', 'Date'],
        as_index=False
    )['Duration (decimal)'].sum()
    
    unique_entries.rename(columns={'Duration (decimal)': 'Duration'}, inplace=True)
    
    return unique_entries


def map_codes(entries: pd.DataFrame):
    def get_codes(row):
        try:
            project_code = int(row['Project'].split('|')[0].strip())
        except (ValueError, IndexError):
            project_code = parameters['default_project_code']
            st.warning(f"Failed to parse project code for row: {row['Project']}. Using default {project_code}")
        
        task_str = row['Task'] if pd.notna(row['Task']) else ''
        try:
            issue_code = int(task_str.split('|')[0].strip())
        except (ValueError, IndexError):
            issue_code = parameters['default_issue_code']
            st.warning(f"Failed to parse issue code for row: {row['Task']}. Using default {issue_code}")

        return [project_code, issue_code]

    entries[['Project Code', 'Issue Code']] = entries.apply(get_codes, axis=1, result_type='expand')
    entries['Duration'] = entries['Duration'].round(2)

    return entries