from datetime import date

import pandas as pd
import streamlit as st

import clockify_api
import process
import upload


def _resolve_api_key() -> str | None:
    try:
        key = st.secrets["clockify"]["api_key"]
        if key and key != "replace-with-your-clockify-api-key":
            return key
    except (KeyError, FileNotFoundError, AttributeError):
        pass
    return st.session_state.get("clockify_api_key") or None


def _get_date_range(period_mode: str) -> tuple[date, date]:
    if period_mode == "Month":
        month_options = clockify_api.recent_month_options()
        labels = [label for label, _ in month_options]
        selected_label = st.selectbox("Month", labels, index=0)
        year, month = dict(month_options)[selected_label]
        return clockify_api.month_bounds(year, month)

    today = date.today()
    default_start = today.replace(day=1)
    selected = st.date_input(
        "Date range",
        value=(default_start, today),
    )
    if isinstance(selected, tuple) and len(selected) == 2:
        return selected[0], selected[1]
    if isinstance(selected, date):
        return selected, selected
    return default_start, today


if "entries" not in st.session_state:
    st.session_state.entries = None

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

st.title("Clockify :arrow_right: TIMS")

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
    st.subheader("Import from Clockify")

    secrets_key = None
    try:
        secrets_key = st.secrets["clockify"]["api_key"]
        if secrets_key == "replace-with-your-clockify-api-key":
            secrets_key = None
    except (KeyError, FileNotFoundError, AttributeError):
        secrets_key = None

    if not secrets_key:
        st.text_input(
            "Clockify API key",
            type="password",
            key="clockify_api_key",
            help="Create an API key in Clockify Profile settings. "
            "For local use, you can also set it in .streamlit/secrets.toml.",
        )

    period_mode = st.radio(
        "Select period",
        ["Month", "Date range"],
        horizontal=True,
    )
    start_date, end_date = _get_date_range(period_mode)

    fetch_record = st.button(label="Fetch Clockify entries")

    if fetch_record:
        api_key = _resolve_api_key()
        if not api_key:
            st.error("Enter your Clockify API key to fetch entries.")
        else:
            try:
                entries, skipped = clockify_api.fetch_time_entries(
                    api_key, start_date, end_date
                )
                if entries.empty:
                    st.warning(
                        f"No completed time entries found between "
                        f"{start_date.strftime('%d/%m/%Y')} and "
                        f"{end_date.strftime('%d/%m/%Y')}."
                    )
                    st.session_state.entries = None
                else:
                    entries = process.remove_duplicates(entries)
                    entries = process.map_codes(entries)
                    entries = entries.sort_values(by="Date")
                    st.session_state.entries = entries
                    if skipped:
                        st.info(
                            f"Skipped {skipped} in-progress time "
                            f"{'entry' if skipped == 1 else 'entries'}."
                        )
                    st.dataframe(st.session_state.entries)
            except clockify_api.ClockifyAPIError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Failed to fetch Clockify entries: {exc}")

    if st.session_state.entries is not None and not fetch_record:
        st.dataframe(st.session_state.entries)

    if st.session_state.entries is not None:
        confirm = st.checkbox("Confirm data is correct before upload")
        upload_record = st.button(
            label="Upload record",
            disabled=not confirm,
        )

        if upload_record:
            username = st.session_state.uuid
            headers = {
                "Referer": (
                    "http://tims.maxwellgeosystems.com/tims/MGS/"
                    f"screen-user-timesheet-input.php?username={st.session_state.name}"
                )
            }
            upload.upload_record(st.session_state.entries, username, headers)
            st.session_state.entries = None
