import oracledb
import os
import csv
import traceback
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

    statements = [s.strip() for s in sql.split(";") if s.strip()]
    for stmt in statements:
        cursor.execute(stmt)


def fetch_query_result(cursor, sql):
    cursor.execute(sql)
    cols = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    return cols, rows


def normalize_result(cols, rows):
    return cols, sorted(rows)


def pretty_result(cols, rows):
    return {
        "columns": cols,
        "rows": rows
    }


def diff_results(expected, actual):
    exp_cols, exp_rows = expected
    act_cols, act_rows = actual

    diff = []

    if exp_cols != act_cols:
        diff.append(
            f"Column mismatch:\n"
            f"Expected: {exp_cols}\n"
            f"Actual:   {act_cols}"
        )

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


def main():
    os.makedirs(LOGS_DIR, exist_ok=True)

    conn = connect()
    cursor = conn.cursor()

    results = []

    # ---------- Compute expected output ----------
    drop_all_tables(cursor)
    run_sql_script(cursor, SCHEMA_FILE)

    with open(MODEL_FILE, "r", encoding="utf-8") as f:
        model_sql = f.read().strip()

    exp_cols, exp_rows = fetch_query_result(cursor, model_sql)
    expected = normalize_result(exp_cols, exp_rows)

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

        try:
            # Fresh schema
            run_sql_script(cursor, SCHEMA_FILE)

            with open(os.path.join(QUERIES_DIR, file), "r", encoding="utf-8") as f:
                student_sql = f.read().strip()

            act_cols, act_rows = fetch_query_result(cursor, student_sql)
            actual = normalize_result(act_cols, act_rows)

            diff = diff_results(expected, actual)

            with open(log_path, "w", encoding="utf-8") as log:
                log.write(f"STUDENT ID: {student_id}\n\n")

                log.write("EXPECTED OUTPUT:\n")
                log.write(pformat(pretty_result(*expected)))
                log.write("\n\n")

                log.write("STUDENT OUTPUT:\n")
                log.write(pformat(pretty_result(*actual)))
                log.write("\n\n")

                if diff:
                    status = "FAIL"
                    log.write("DIFF:\n")
                    log.write(diff)
                else:
                    status = "PASS"
                    log.write("RESULT: PASS")

        except Exception as e:
            status = "FAIL"
            with open(log_path, "w", encoding="utf-8") as log:
                log.write(f"STUDENT ID: {student_id}\n\n")
                log.write("SQL ERROR:\n")
                log.write(str(e) + "\n\n")
                log.write(traceback.format_exc())

        finally:
            drop_all_tables(cursor)
            conn.commit()

        print(f"➡ Result: {status}")
        results.append([student_id, status])

    # ---------- Export CSV ----------
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["StudentID", "Result"])
        writer.writerows(results)

    cursor.close()
    conn.close()

    print("\nEvaluation complete. Results written to results.csv")


if __name__ == "__main__":
    main()
