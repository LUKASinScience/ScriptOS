from pathlib import Path

from app.discovery.risk_scan import scan_risks

FIXTURES = Path(__file__).parent / "fixtures"


def test_flags_known_risky_patterns():
    risks = scan_risks(str(FIXTURES / "risky_script.py"))
    joined = " ".join(risks)
    assert "eval" in joined
    assert "system" in joined
    assert "pickle" in joined or "loads" in joined


def test_clean_script_has_no_findings():
    assert scan_risks(str(FIXTURES / "analyze.py")) == []


def test_missing_file_returns_empty_not_error():
    assert scan_risks(str(FIXTURES / "does_not_exist.py")) == []


if __name__ == "__main__":
    test_flags_known_risky_patterns()
    test_clean_script_has_no_findings()
    test_missing_file_returns_empty_not_error()
    print("ok")
