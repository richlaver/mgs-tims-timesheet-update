import pandas as pd
import streamlit as st


def read_clockify_csv(file):
    entries = pd.read_csv(
        filepath_or_buffer=file,
        usecols=[
            'Project',
            'Task',
            'Description',
            'Start Date',
            'Start Time',
            'End Date',
            'End Time',
            'Duration (decimal)'
        ],
        dayfirst=True,
        parse_dates={
            'Start Datetime': ['Start Date', 'Start Time'],
            'End Datetime': ['End Date', 'End Time']
        }
    )

    entries['End Datetime'] = pd.to_datetime(entries['End Datetime'])
    entries['Start Datetime'] = pd.to_datetime(entries['Start Datetime'])
    entries['Date'] = entries['End Datetime'].dt.date
    
    return entries