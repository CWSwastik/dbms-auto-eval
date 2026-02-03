import oracledb
import os
import csv
import traceback
import re
from pprint import pformat

# ---------------- CONFIG ----------------

ORACLE_USER = "system"
ORACLE_PASSWORD = "manager"
ORACLE_DSN = "localhost:1521/FREEPDB1"

SCHEMA_FILE = "schema.sql"
MODEL_FILE = "model_solution.sql"
QUERIES_DIR = "queries"
LOGS_DIR = "logs"
OUTPUT_CSV = "results.csv"

EXPECTED_QUERIES = 2  # Set this to the number of queries in the assignment

# ---------------------------------------


def connect():
    return oracledb.connect(
        user=ORACLE_USER,
        password=ORACLE_PASSWORD,
        dsn=ORACLE_DSN
    )


def run_sql_script(cursor, path):
    with open(path, "r", encoding="utf-8") as f:
        sql = f.read()

    # Split by semicolon but ignore ones inside strings (simplified)
    # For actual labs, students usually write simple queries
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    for stmt in statements:
        try:
            cursor.execute(stmt)
        except Exception:
            # Oracle doesn't have 'IF NOT EXISTS', so we might ignore some errors during schema setup
            pass


def fetch_query_result(cursor, sql):
    if not sql:
        return None
    cursor.execute(sql)
    cols = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    return cols, rows


def normalize_result(cols, rows):
    if rows is None:
        return None
    return cols, sorted(rows)


def pretty_result(cols, rows):
    if rows is None:
        return "NO RESULT"
    return {
        "columns": cols,
        "rows": rows
    }


def diff_results(expected, actual):
    if expected is None:
        return "No expected result provided."
    if actual is None:
        return "No actual result provided (student query missing or failed)."

    exp_cols, exp_rows = expected
    act_cols, act_rows = actual

    diff = []

    if exp_cols != act_cols:
        diff.append(
            f"Column mismatch:\n"
            f"Expected: {exp_cols}\n"
            f"Actual:   {act_cols}"
        )

    # Convert rows (which are tuples) to sets for easier comparison
    missing = set(exp_rows) - set(act_rows)
    extra = set(act_rows) - set(exp_rows)

    if missing:
        diff.append(f"Missing rows:\n{pformat(missing)}")

    if extra:
        diff.append(f"Extra rows:\n{pformat(extra)}")

    return "\n\n".join(diff)


def drop_all_tables(cursor):
    cursor.execute("SELECT table_name FROM user_tables")
    for (table_name,) in cursor.fetchall():
        try:
            cursor.execute(f'DROP TABLE "{table_name}" PURGE')
        except Exception:
            pass


def parse_queries(content, expected_count):
    queries = {}
    for i in range(1, expected_count + 1):
        # Look for --N-- followed by anything until the next --M-- or end of file
        marker = f"--{i}--"
        pattern = rf"{marker}\s*(.*?)\s*(?=--\d+--|$)"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            queries[i] = match.group(1).strip()
        else:
            queries[i] = None
    return queries


def main():
    os.makedirs(LOGS_DIR, exist_ok=True)

    conn = connect()
    cursor = conn.cursor()

    results = []

    # ---------- Compute expected outputs ----------
    print("Pre-computing expected results from model solution...")
    with open(MODEL_FILE, "r", encoding="utf-8") as f:
        model_content = f.read()

    model_queries = parse_queries(model_content, EXPECTED_QUERIES)
    expected_results = {}

    for i in range(1, EXPECTED_QUERIES + 1):
        drop_all_tables(cursor)
        run_sql_script(cursor, SCHEMA_FILE)
        
        sql = model_queries.get(i)
        if sql:
            try:
                exp_cols, exp_rows = fetch_query_result(cursor, sql)
                expected_results[i] = normalize_result(exp_cols, exp_rows)
            except Exception as e:
                print(f"Error in model solution Query {i}: {e}")
                expected_results[i] = None
        else:
            print(f"Warning: Model query {i} not found in {MODEL_FILE}")
            expected_results[i] = None

    conn.commit()
    drop_all_tables(cursor)
    conn.commit()

    # ---------- Evaluate students ----------
    for file in sorted(os.listdir(QUERIES_DIR)):
        if not file.endswith(".sql"):
            continue

        student_id = file.replace(".sql", "")
        log_path = os.path.join(LOGS_DIR, f"{student_id}.log")

        print(f"\nEvaluating student: {student_id}")
        
        student_scores = {}
        
        with open(os.path.join(QUERIES_DIR, file), "r", encoding="utf-8") as f:
            student_content = f.read()
        
        student_queries = parse_queries(student_content, EXPECTED_QUERIES)

        with open(log_path, "w", encoding="utf-8") as log:
            log.write(f"STUDENT ID: {student_id}\n")
            log.write("=" * 30 + "\n\n")

            for i in range(1, EXPECTED_QUERIES + 1):
                log.write(f"--- QUERY {i} ---\n")
                status = "FAIL"
                try:
                    # Fresh schema for each query to avoid side effects
                    drop_all_tables(cursor)
                    run_sql_script(cursor, SCHEMA_FILE)

                    sql = student_queries.get(i)
                    if not sql:
                        log.write("STATUS: FAIL (Marker not found or empty)\n\n")
                    else:
                        act_cols, act_rows = fetch_query_result(cursor, sql)
                        actual = normalize_result(act_cols, act_rows)
                        expected = expected_results.get(i)

                        diff = diff_results(expected, actual)

                        log.write("EXPECTED OUTPUT:\n")
                        log.write(pformat(pretty_result(*expected)) if expected else "N/A")
                        log.write("\n\n")

                        log.write("STUDENT OUTPUT:\n")
                        log.write(pformat(pretty_result(*actual)))
                        log.write("\n\n")

                        if diff:
                            log.write("DIFF:\n")
                            log.write(diff + "\n")
                        else:
                            status = "PASS"
                            log.write("RESULT: PASS\n")
                        
                except Exception as e:
                    log.write("SQL ERROR:\n")
                    log.write(str(e) + "\n\n")
                    log.write(traceback.format_exc() + "\n")
                
                student_scores[f"Q{i}"] = status
                log.write(f"FINAL STATUS: {status}\n")
                log.write("-" * 20 + "\n\n")

        pass_count = list(student_scores.values()).count("PASS")
        print(f"➡ Score: {pass_count}/{EXPECTED_QUERIES}")
        
        row = [student_id]
        for i in range(1, EXPECTED_QUERIES + 1):
            row.append(student_scores[f"Q{i}"])
        row.append(f"{pass_count}/{EXPECTED_QUERIES}")
        results.append(row)

    # ---------- Export CSV ----------
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        header = ["StudentID"] + [f"Q{i}" for i in range(1, EXPECTED_QUERIES + 1)] + ["Total"]
        writer.writerow(header)
        writer.writerows(results)

    cursor.close()
    conn.close()

    print(f"\nEvaluation complete. Results written to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
