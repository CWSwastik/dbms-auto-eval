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

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Step 3: Project Structure

```
auto-eval/
│
├── main.py                # Evaluation script
├── check_format.py        # OPTIONAL: Format validator for students
├── schema.sql             # Schema + data setup
├── model_solution.sql     # Correct solution (with --N-- markers)
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
└── results.csv            # Final grades (Q1, Q2, ..., Total)
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

Must contain queries preceded by markers `--N--`:

```sql
--1--
SELECT * FROM Student WHERE marks > 95;

--2--
SELECT name FROM Student ORDER BY marks DESC;
```

These outputs are treated as the **expected answers** for each question.

---

## Step 6: Student SQL files

Each student submits **one `.sql` file** following the same `--N--` marker format:

```sql
--1--
SELECT * FROM Student WHERE marks > 95;

--2--
SELECT name FROM Student ORDER BY marks DESC;
```

* File name = **Student ID** (e.g. `2023A7PS0043H.sql`)
* Each query is evaluated independently.
* SQL errors in one query do not affect others.

---

## Step 7: Format Checker (For Students)

Students should verify their file format before submission using `check_format.py`.

```bash
python check_format.py 2023A7PS0043H.sql
```

This script checks:
1. If the **filename** is a valid Student ID.
2. If all **query markers** (`--1--`, `--2--`, etc.) are present.
3. If each query ends with a **semicolon**.

---

## Step 8: Run the evaluator

```bash
python main.py
```

---

## Console Output Example

```
Evaluating student: 2023A7PS0043H
➡ Score: 2/2

Evaluating student: 2023A7PS0101H
➡ Score: 1/2

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

## Step 9: Run the Submission Server (Streamlit)

To host the submission portal where students can upload and check their files:

```bash
streamlit run app.py
```

- The server will be available at `http://localhost:8501`.
- It performs real-time formatting and syntax checks before allowing submission.
- Submissions are stored in the `queries/` directory.

---

## Instructor Configuration

### 1. Setting Expected Query Count
You must set the `EXPECTED_QUERIES` variable in **two** files to match your assignment:
- `main.py`: Used by the evaluation script.
- `check_format.py`: Used by the student script and the Streamlit app.

### 2. Setting Expected Solutions
- Edit `model_solution.sql` and provide the correct SQL queries for each marker (e.g., `--1--`, `--2--`).
- These queries will be executed against `schema.sql` to generate the "ground truth" for grading.

### 3. Setting Database Schema
- Edit `schema.sql` to include all `CREATE TABLE` and `INSERT` statements needed for the lab environment.

---

## Final Output (`results.csv`)

```csv
StudentID,Q1,Q2,Total
2023A7PS0043H,PASS,PASS,2/2
2023A7PS0101H,FAIL,PASS,1/2
```
