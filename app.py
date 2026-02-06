import streamlit as st
import os
import re
from check_format import is_valid_student_id_file, EXPECTED_QUERIES

import json
import hashlib
from datetime import datetime
from streamlit import runtime
from streamlit.runtime.scriptrunner import get_script_run_ctx

# --- CONFIG ---
QUERIES_DIR = "queries"
SUBMISSIONS_LOG = "submissions_tracking.json"
EVENTS_LOG = "submission_events.log"
os.makedirs(QUERIES_DIR, exist_ok=True)

if not os.path.exists(SUBMISSIONS_LOG):
    with open(SUBMISSIONS_LOG, "w") as f:
        json.dump({"ip_to_id": {}, "id_to_ip": {}}, f)

st.set_page_config(page_title="DBS Lab Query Submission")

def get_remote_ip():
    """Get remote IP using Streamlit's internal runtime."""
    try:
        ctx = get_script_run_ctx()
        if ctx is None:
            return "unknown"
        session_info = runtime.get_instance().get_client(ctx.session_id)
        if session_info is None:
            return "unknown"
        return session_info.request.remote_ip
    except Exception:
        return "unknown"

def get_client_info():
    """Collects client information for logging."""
    try:
        headers = st.context.headers
        return {
            "host": headers.get("Host", "unknown"),
            "user_agent": headers.get("User-Agent", "unknown"),
        }
    except Exception:
        return {"host": "unknown", "user_agent": "unknown"}

def load_tracking():
    with open(SUBMISSIONS_LOG, "r") as f:
        data = json.load(f)
        if "ip_to_id" not in data:
            data = {"ip_to_id": {}, "id_to_ip": {}}
        return data

def save_tracking(tracking):
    with open(SUBMISSIONS_LOG, "w") as f:
        json.dump(tracking, f, indent=4)

def log_event(event_type, student_id, ip, client_info, extra=""):
    """Logs an event to the events log file."""
    timestamp = datetime.now().isoformat()
    log_line = (
        f"[{timestamp}] [{event_type}] "
        f"ID: {student_id} | IP: {ip} | "
        f"Host: {client_info['host']} | "
        f"UA: {client_info['user_agent'][:60]}... | "
        f"{extra}\n"
    )
    with open(EVENTS_LOG, "a", encoding="utf-8") as log:
        log.write(log_line)

def get_content_hash(content):
    """Returns a short hash of the content for change detection."""
    return hashlib.md5(content.encode()).hexdigest()[:8]

import sqlglot
from sqlglot import parse_one, exp
from sqlglot.errors import ParseError

def check_format_streamlit(content, expected_count):
    all_passed = True
    results = []
    
    for i in range(1, expected_count + 1):
        marker = f"--{i}--"
        # Regex to find the marker and capture the query until the next marker or EOF
        pattern = rf"{re.escape(marker)}\s*(.*?)\s*(?=--\d+--|$)"
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            query_text = match.group(1).strip()
            if query_text:
                status = "PASS"
                msg = "Correctly formatted."
                
                # Check for trailing semicolon
                if not query_text.endswith(';'):
                    status = "WARNING"
                    msg = "Marker found, but query might be missing a semicolon."
                
                # --- Syntax Checking (Oracle) ---
                try:
                    # Strip semicolon for parsing if it exists, as sqlglot handles single statements
                    clean_sql = query_text.rstrip(';').strip()
                    parse_one(clean_sql, read="oracle")
                except ParseError as e:
                    # If we already have a warning, we append to it, otherwise we downgrade to WARNING or stay FAIL
                    # Since syntax is a warning, we use WARNING status if it's not already FAIL
                    syntax_msg = f"Potential Oracle syntax error: {str(e)[:100]}..."
                    if status != "FAIL":
                        status = "WARNING"
                        msg = f"{msg} {syntax_msg}" if msg != "Correctly formatted." else syntax_msg
                except Exception as e:
                    syntax_msg = "Could not validate syntax (unexpected error)."
                    if status != "FAIL":
                        status = "WARNING"
                        msg = f"{msg} {syntax_msg}" if msg != "Correctly formatted." else syntax_msg

                results.append((i, status, msg))
            else:
                results.append((i, "FAIL", f"Marker {marker} found, but no query follows it."))
                all_passed = False
        else:
            results.append((i, "FAIL", f"Marker {marker} is missing."))
            all_passed = False
            
    return all_passed, results

def main():
    st.title("DBS Lab Query Submission")
    
    # --- Example SQL File Generation ---
    example_sql = "--1--\nSELECT * FROM Student;\n\n--2--\nSELECT COUNT(*) FROM Student;"
    
    st.markdown(f"""
    Welcome! Please upload your SQL file for evaluation.
    
    **Requirements:**
    1. Filename must be your Student ID (e.g., `2023A7PS0043H.sql`).
    2. Must contain exactly **{EXPECTED_QUERIES}** queries.
    3. Each query must be marked with `--1--`, `--2--`, etc.
    """)
    
    st.download_button(
        label="📥 Download Example SQL File",
        data=example_sql,
        file_name="2023A7PS0000H.sql",
        mime="text/sql",
        help="Use this as a template for your submission"
    )

    uploaded_file = st.file_uploader("Choose a .sql file", type="sql")

    if uploaded_file is not None:
        filename = uploaded_file.name
        
        # Initialize session state for this specific file
        if "last_uploaded_file" not in st.session_state or st.session_state.last_uploaded_file != filename:
            st.session_state.last_uploaded_file = filename
            st.session_state.format_passed = False
            st.session_state.check_done = False

        # 1. Check filename
        if not is_valid_student_id_file(filename):
            st.error(f"❌ **Invalid filename:** `{filename}`")
            st.info("Your file MUST be named as your Student ID (e.g., `2023A7PS0043H.sql`).")
            return

        content = uploaded_file.read().decode("utf-8")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Check Format", use_container_width=True):
                passed, results = check_format_streamlit(content, EXPECTED_QUERIES)
                st.session_state.format_passed = passed
                st.session_state.check_done = True
                st.session_state.results = results

        with col2:
            submit_disabled = not st.session_state.get("format_passed", False)
            if st.button("Submit Query", use_container_width=True, disabled=submit_disabled, type="primary"):
                user_ip = get_remote_ip()
                client_info = get_client_info()
                tracking = load_tracking()
                
                # Extract Student ID from filename (e.g. 2023A7PS0043H)
                student_id = filename.replace(".sql", "").upper()
                content_hash = get_content_hash(content)
                
                # Rule 1: Check if this IP already submitted for a DIFFERENT ID
                existing_id_for_ip = tracking["ip_to_id"].get(user_ip)
                
                # Rule 2: Check if this ID was already submitted by a DIFFERENT IP
                existing_ip_for_id = tracking["id_to_ip"].get(student_id)
                
                if existing_id_for_ip and existing_id_for_ip != student_id:
                    # This IP already submitted for a different student ID
                    st.error(f"❌ **Blocking Submission:** You have already submitted for Student ID `{existing_id_for_ip}`. You cannot submit for a different ID.")
                    log_event(
                        "BLOCKED", student_id, user_ip, client_info,
                        f"Reason: IP already linked to {existing_id_for_ip}"
                    )
                elif existing_ip_for_id and existing_ip_for_id != user_ip:
                    # This student ID was already submitted from a different IP
                    st.error(f"❌ **Blocking Submission:** Student ID `{student_id}` has already been submitted from a different IP address. If this is an error, contact the instructor.")
                    log_event(
                        "BLOCKED", student_id, user_ip, client_info,
                        f"Reason: ID already claimed by IP {existing_ip_for_id}"
                    )
                else:
                    # Check if this is a new submission or an update
                    is_update = existing_id_for_ip == student_id
                    
                    # Store the file
                    save_path = os.path.join(QUERIES_DIR, filename)
                    with open(save_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    
                    # Update tracking (bidirectional mapping)
                    tracking["ip_to_id"][user_ip] = student_id
                    tracking["id_to_ip"][student_id] = user_ip
                    save_tracking(tracking)
                    
                    event_type = "UPDATE" if is_update else "SUBMIT"
                    log_event(
                        event_type, student_id, user_ip, client_info,
                        f"Hash: {content_hash} | File: {filename}"
                    )
                    
                    if is_update:
                        st.success(f"✅ **Submission Updated!**")
                        st.info(f"Your file `{filename}` has been updated.")
                    else:
                        st.success(f"✅ **Submission Successful!**")

        # Show results if check was performed
        if st.session_state.get("check_done", False):
            st.subheader("Formatting Check Results")
            for q_num, status, msg in st.session_state.results:
                if status == "PASS":
                    st.success(f"**Query {q_num}:** {msg}")
                elif status == "WARNING":
                    st.warning(f"**Query {q_num}:** {msg}")
                else:
                    st.error(f"**Query {q_num}:** {msg}")

            if st.session_state.format_passed:
                st.success("✅ **Formatting checks passed!** You can now submit.")
            else:
                st.error("❌ **Formatting errors found.** Please fix your file and check again.")

if __name__ == "__main__":
    main()
