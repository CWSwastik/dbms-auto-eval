# Oracle SQL Auto-Evaluation Script

This script automatically evaluates student SQL queries against a model solution.
Each student query is executed on a **fresh schema**, compared with the expected output, and graded as **PASS/FAIL**.
Detailed diffs and SQL errors are written to per-student log files.

---

## Requirements

Note: Docker is optional, if you already have an Oracle Database (XE / Free / 21c / 23c) installed, you can skip Step 1. You may need to change ORACLE_DSN in the config section of main.py to localhost:1521/XE etc.

* Python **3.9+**
* Docker
* Internet access (to pull Oracle Docker image)

---

## Step 1: Run Oracle Database using Docker

We use the official lightweight Oracle image by **gvenzl**.

### Start Oracle (one-time setup)

```bash
docker run -d \
  -p 1521:1521 \
  -e ORACLE_PASSWORD=manager \
  --name oracle-23ai \
  gvenzl/oracle-free
```

⏳ First startup takes **2–5 minutes**.

---

### Verify Oracle is running

```bash
docker ps
```

You should see `gvenzl/oracle-free` running.



---

## Step 2: Install Python dependencies

Create a virtual environment (recommended):

```bash
python -m venv venv
venv\Scripts\activate   # Windows
source venv/bin/activate  # Linux/macOS
```

Install dependency:

```bash
pip install oracledb
```

---

## Step 3: Project Structure

```
auto-eval/
│
├── main.py                # Evaluation script
├── schema.sql             # Schema + data setup
├── model_solution.sql     # Correct solution
│
├── queries/               # Student submissions
│   ├── 2023A7PS0043H.sql
│   ├── 2023A7PS0101H.sql
│   └── ...
│
├── logs/                  # Auto-created
│   ├── 2023A7PS0043H.log
│   └── 2023A7PS0101H.log
│
└── results.csv            # Final grades
```

---

## Step 4: Writing `schema.sql`

Example:

```sql
CREATE TABLE Student (
    id NUMBER PRIMARY KEY,
    name VARCHAR2(50),
    marks NUMBER
);

INSERT INTO Student VALUES (1, 'Swastik', 99);
INSERT INTO Student VALUES (2, 'Sid', 98);
```

The script **automatically drops all tables** after evaluating each student and re run's the schema.sql

---

## Step 5: Writing `model_solution.sql`

Must contain **one SELECT query**:

```sql
SELECT * FROM Student WHERE marks > 95;
```

This output is treated as the **expected answer**.

---

## Step 6: Student SQL files

Each student submits **one `.sql` file**:

```
queries/2023A7PS0043H.sql
```

Example:

```sql
SELECT * FROM Student WHERE marks > 95;
```

* File name = **Student ID**
* SQL errors → **FAIL**
* Output mismatch → **FAIL**

---

## Step 7: Run the evaluator

```bash
python main.py
```

---

## Console Output Example

```
Evaluating student: 2023A7PS0043H
➡ Result: PASS

Evaluating student: 2023A7PS0101H
➡ Result: FAIL

✅ Evaluation complete. Results written to results.csv
```

---

## Logs Format (per student)

Example: `logs/2023A7PS0101H.log`

```
STUDENT ID: 2023A7PS0101H

EXPECTED OUTPUT:
{'columns': ['ID', 'NAME', 'MARKS'],
 'rows': [(1, 'Swastik', 99), (2, 'Sid', 98)]}

STUDENT OUTPUT:
{'columns': ['ID', 'NAME', 'MARKS'],
 'rows': [(1, 'Swastik', 99)]}

DIFF:
Missing rows:
{(2, 'Sid', 98)}
```

---

## Final Output (`results.csv`)

```csv
StudentID,Result
2023A7PS0043H,PASS
2023A7PS0101H,FAIL
```
