import sys
import re
import os

# --- INSTRUCTOR CONFIGURATION ---
EXPECTED_QUERIES = 2
# --------------------------------

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_banner():
    print(f"{Colors.HEADER}{Colors.BOLD}========================================={Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}       DB LAB SQL FORMAT CHECKER         {Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}========================================={Colors.ENDC}\n")

def is_valid_student_id_file(filename):
    pattern = r"^\d{4}[A-Z0-9]{4}\d{4}[A-Z]\.sql$"
    return re.match(pattern, filename, re.IGNORECASE) is not None

def check_format(filename, expected_count):
    if not os.path.exists(filename):
        print(f"{Colors.FAIL}{Colors.BOLD}Error:{Colors.ENDC} File '{filename}' not found.")
        print(f"Please ensure your file is in the same folder as this script or provide the full path.")
        return False

    base_name = os.path.basename(filename)
    if not is_valid_student_id_file(base_name):
        print(f"{Colors.FAIL}{Colors.BOLD}Error:{Colors.ENDC} Invalid filename '{base_name}'.")
        print(f"Your file MUST be named as your {Colors.BOLD}Student ID{Colors.ENDC} (e.g., 2023A7PS0043H.sql).")
        print(f"Generic names like 'submission.sql' or 'ans.sql' are {Colors.BOLD}NOT{Colors.ENDC} accepted.")
        return False

    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"Checking {Colors.OKCYAN}{filename}{Colors.ENDC} for {Colors.BOLD}{expected_count}{Colors.ENDC} queries...\n")
    
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
                if not query_text.endswith(';'):
                    print(f"Query {i}: {Colors.WARNING}[WARN]{Colors.ENDC} Marker found, but query might be missing a semicolon.")
                else:
                    print(f"Query {i}: {Colors.OKGREEN}[PASS]{Colors.ENDC} Correctly formatted.")
                results.append(True)
            else:
                print(f"Query {i}: {Colors.FAIL}[FAIL]{Colors.ENDC} Marker {marker} found, but no query follows it.")
                results.append(False)
                all_passed = False
        else:
            print(f"Query {i}: {Colors.FAIL}[FAIL]{Colors.ENDC} Marker {marker} is missing.")
            results.append(False)
            all_passed = False

    print("\n" + "-" * 41)
    if all_passed:
        print(f"{Colors.OKGREEN}{Colors.BOLD}SUMMARY: ALL FORMATTING CHECKS PASSED!{Colors.ENDC}")
        print("You are ready to submit your file.")
    else:
        print(f"{Colors.FAIL}{Colors.BOLD}SUMMARY: FORMATTING ERRORS FOUND.{Colors.ENDC}")
        print("Please fix the issues above before submitting.")
    print("-" * 41)
    
    return all_passed

def main():
    if os.name == 'nt':
        os.system('')

    print_banner()

    target_file = None
    expected = EXPECTED_QUERIES

    if len(sys.argv) > 1:
        # Check if first arg is a number or filename
        if sys.argv[1].isdigit():
            expected = int(sys.argv[1])
        else:
            target_file = sys.argv[1]
    
    if len(sys.argv) > 2:
        if sys.argv[2].isdigit():
            expected = int(sys.argv[2])

    if not target_file:
        print(f"{Colors.WARNING}Usage:{Colors.ENDC} python check_format.py <your_student_id>.sql")
        # List .sql files in directory to help the student
        sql_files = [f for f in os.listdir('.') if f.endswith('.sql')]
        if sql_files:
            print(f"\nFound these .sql files in the folder:")
            for f in sql_files:
                print(f" - {f}")
        return

    check_format(target_file, expected)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
