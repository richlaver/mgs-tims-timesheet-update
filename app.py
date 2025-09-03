import streamlit as st
import pandas as pd
import upload
import input
import process

if 'entries' not in st.session_state:
    st.session_state.entries = None

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

st.title('Clockify :arrow_right: TIMS')

if not st.session_state.logged_in:
    name = st.text_input("Enter your TIMS name")
    uuid = st.text_input("Enter your TIMS UUID")
    if st.button("Login"):
        if name and uuid:
            st.session_state.name = name
            st.session_state.uuid = uuid
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Please enter both name and UUID")
else:
    uploaded_files = st.file_uploader("Upload Clockify CSV(s)", type="csv", accept_multiple_files=True)

    convert_record = st.button(label='Convert record')

    if convert_record and uploaded_files:
        entries = pd.DataFrame()
        for file in uploaded_files:
            df = input.read_clockify_csv(file)
            entries = pd.concat([entries, df])
        
        entries = process.remove_duplicates(entries)
        entries = process.map_codes(entries)
        entries = entries.sort_values(by='Date')
        st.session_state.entries = entries
        st.dataframe(st.session_state.entries)

    if st.session_state.entries is not None:
        confirm = st.checkbox("Confirm data is correct before upload")
        upload_record = st.button(
            label='Upload record',
            disabled=not confirm
        )

        if upload_record:
            username = st.session_state.uuid
            headers = {'Referer': f'http://tims.maxwellgeosystems.com/tims/MGS/screen-user-timesheet-input.php?username={st.session_state.name}'}
            upload.upload_record(st.session_state.entries, username, headers)
            st.session_state.entries = None