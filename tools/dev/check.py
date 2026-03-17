"""
Quality gate for codex-tools library.
Simplified version: uses pre-commit, mypy, pip-audit, and pytest.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# --- Configuration ---
PROJECT_ROOT = Path(__file__).parent.parent.parent
SRC_DIR = PROJECT_ROOT / "src"
TESTS_DIR = PROJECT_ROOT / "tests"


# ANSI Colors
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def print_step(msg: str) -> None:
    print(f"\n{Colors.YELLOW}🔍 {msg}...{Colors.ENDC}")


def print_success(msg: str) -> None:
    print(f"{Colors.GREEN}✅ {msg}{Colors.ENDC}")


def print_error(msg: str) -> None:
    print(f"{Colors.RED}❌ {msg}{Colors.ENDC}")


def run_command(command: str, cwd: Path = PROJECT_ROOT, capture_output: bool = False) -> tuple[bool, str]:
    """Runs a system command and returns result."""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            check=False,
            text=True,
            capture_output=capture_output,
        )
        return result.returncode == 0, result.stdout or result.stderr or ""
    except Exception as e:
        return False, str(e)


# --- Check Functions ---


def check_quality() -> bool:
    print_step("Running Quality Hooks (pre-commit: Ruff, Format, Bandit)")
    success, out = run_command("pre-commit run --all-files")
    if not success:
        print_error(f"Pre-commit failed:\n{out}")
        return False
    print_success("Quality hooks passed.")
    return True


def check_types() -> bool:
    print_step("Checking Types (Mypy)")
    success, out = run_command(f"mypy {SRC_DIR}", capture_output=True)
    if not success:
        print_error(f"Mypy check failed:\n{out}")
    else:
        print_success("Mypy check passed.")
    return success


def check_security() -> bool:
    print_step("Security Audit (pip-audit)")
    success, out = run_command("pip-audit", capture_output=True)
    if not success:
        print_error(f"Security audit failed:\n{out}")
    else:
        print_success("Security audit passed.")
    return success


def run_tests(marker: str = "unit") -> bool:
    print_step(f"Running {marker.capitalize()} Tests")
    success, _ = run_command(f"pytest {TESTS_DIR} -m {marker} -v --tb=short")
    if success:
        print_success(f"{marker.capitalize()} tests passed.")
    else:
        print_error(f"{marker.capitalize()} tests failed.")
    return success


# --- Main Logic ---


def run_all() -> None:
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")

    print(f"{Colors.HEADER}{Colors.BOLD}=== codex-tools quality gate ==={Colors.ENDC}")

    if not check_quality():
        sys.exit(1)
    if not check_types():
        sys.exit(1)
    if not check_security():
        sys.exit(1)

    if not run_tests("unit"):
        sys.exit(1)

    choice = input(f"\n{Colors.YELLOW}🚀 Run Integration Tests? (Requires Redis) [y/N]: {Colors.ENDC}").lower()
    if choice == "y" and not run_tests("integration"):
        sys.exit(1)

    print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ALL CHECKS PASSED!{Colors.ENDC}")


def interactive_menu() -> None:
    while True:
        print(f"\n{Colors.CYAN}{Colors.BOLD}🛠 codex-tools Quality Tool{Colors.ENDC}")
        print("1. Fast Check (Pre-commit: Lint, Format, Bandit)")
        print("2. Type Check (Mypy)")
        print("3. Run Unit Tests")
        print("4. Run Integration Tests (Requires Redis)")
        print("5. Security Audit (pip-audit)")
        print("6. Run Everything")
        print("0. Exit")

        choice = input(f"\n{Colors.YELLOW}Select an option [6]: {Colors.ENDC}").strip() or "6"

        if choice == "1":
            check_quality()
        elif choice == "2":
            check_types()
        elif choice == "3":
            run_tests("unit")
        elif choice == "4":
            run_tests("integration")
        elif choice == "5":
            check_security()
        elif choice == "6":
            run_all()
        elif choice == "0":
            break
        else:
            print_error("Invalid choice")


def main() -> None:
    parser = argparse.ArgumentParser(description="codex-tools quality gate")
    parser.add_argument("--all", action="store_true", help="Run all checks")
    parser.add_argument("--lint", action="store_true", help="Run pre-commit hooks")
    parser.add_argument("--types", action="store_true", help="Run mypy")
    parser.add_argument("--security", action="store_true", help="Run pip-audit")
    parser.add_argument("--tests", choices=["unit", "integration", "all"], help="Run specified tests")
    parser.add_argument("--menu", action="store_true", help="Open interactive menu")

    args = parser.parse_args()

    if args.all:
        run_all()
    elif args.lint:
        sys.exit(0 if check_quality() else 1)
    elif args.types:
        sys.exit(0 if check_types() else 1)
    elif args.security:
        sys.exit(0 if check_security() else 1)
    elif args.tests:
        if args.tests == "all":
            u = run_tests("unit")
            i = run_tests("integration")
            sys.exit(0 if u and i else 1)
        else:
            sys.exit(0 if run_tests(args.tests) else 1)
    elif args.menu:
        interactive_menu()
    else:
        interactive_menu()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.RED}Aborted.{Colors.ENDC}")
        sys.exit(1)
