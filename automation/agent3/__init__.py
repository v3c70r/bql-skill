"""Agent 3 Auditor automation script."""
from agent3.auditor import Auditor

if __name__ == "__main__":
    auditor = Auditor()
    auditor.run_full_audit()
