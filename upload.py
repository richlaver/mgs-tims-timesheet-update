import requests as rq
import pandas as pd
import streamlit as st
import concurrent.futures
from data import parameters


def upload_entry(entry: pd.Series, username: str, headers: dict):
    url = parameters['url']
    data = {
        'Projects': entry['Project Code'],
        'username': username,
        'SearchedBug': entry['Issue Code'],
        'TimeEntryDate': entry['Date'].strftime('%d/%m/%Y'),
        'Comments': entry['Description'],
        'Duration': entry['Duration']
    }

    response = rq.post(
        url=url,
        headers=headers,
        data=data
    )
    
    return response


def upload_record(entries: pd.DataFrame, username: str, headers: dict):
    def upload_wrapper(entry):
        response = upload_entry(entry, username, headers)
        return response, entry

    total_entries = len(entries)
    progress_bar = st.progress(0)
    status_text = st.empty()
    failed = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(upload_wrapper, entry) for _, entry in entries.iterrows()]
        
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            response, entry = future.result()
            if response.status_code != 200:
                failed.append(entry)
            
            completed += 1
            progress = completed / total_entries
            progress_bar.progress(progress)
            status_text.text(f'Uploading entry {completed} of {total_entries}...')

    if failed:
        with st.expander("Failed Uploads"):
            st.dataframe(pd.DataFrame(failed))
    
    st.success('Upload complete!')