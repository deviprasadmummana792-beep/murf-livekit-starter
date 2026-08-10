import os
import json
import pytest
from pathlib import Path
import sys

# Add src directory to system path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import schemes_checker
from agent import Assistant
from livekit.agents import RunContext

def test_match_scheme():
    assert schemes_checker.match_scheme("PM Jan Dhan") == "pm_jan_dhan"
    assert schemes_checker.match_scheme("APY") == "atal_pension"
    assert schemes_checker.match_scheme("Atal Pension Yojana") == "atal_pension"
    assert schemes_checker.match_scheme("Sukanya Samriddhi") == "sukanya_samriddhi"
    assert schemes_checker.match_scheme("ssy") == "sukanya_samriddhi"
    assert schemes_checker.match_scheme("PM-KISAN") == "pm_kisan"
    assert schemes_checker.match_scheme("mudra") == "pm_mudra"
    assert schemes_checker.match_scheme("pmjjby") == "pmjjby"
    assert schemes_checker.match_scheme("pmsby") == "pmsby"
    assert schemes_checker.match_scheme("unknown scheme") is None

def test_pm_jan_dhan_eligibility():
    # Age missing
    res = schemes_checker.check_eligibility("PM Jan Dhan")
    assert res["eligible"] == "unknown"
    assert "age" in res["missing_information"]
    
    # Age too young
    res = schemes_checker.check_eligibility("PM Jan Dhan", age=5)
    assert res["eligible"] == "false"
    
    # Age eligible
    res = schemes_checker.check_eligibility("PM Jan Dhan", age=12)
    assert res["eligible"] == "true"
    assert res["verified_date"] == "2026-08-10"

def test_pm_kisan_eligibility():
    # Missing information
    res = schemes_checker.check_eligibility("PM-KISAN")
    assert res["eligible"] == "unknown"
    assert "is_farmer" in res["missing_information"]
    
    # Non-farmer
    res = schemes_checker.check_eligibility("PM-KISAN", is_farmer=False)
    assert res["eligible"] == "false"
    
    # Farmer
    res = schemes_checker.check_eligibility("PM-KISAN", is_farmer=True)
    assert res["eligible"] == "true"
    
    # Inferred from occupation
    res = schemes_checker.check_eligibility("PM-KISAN", occupation="I am a farmer")
    assert res["eligible"] == "true"
    
    # Non-farmer inferred from occupation
    res = schemes_checker.check_eligibility("PM-KISAN", occupation="I am a student")
    assert res["eligible"] == "false"

def test_atal_pension_eligibility():
    # Missing info
    res = schemes_checker.check_eligibility("Atal Pension Yojana")
    assert res["eligible"] == "unknown"
    assert "age" in res["missing_information"]
    
    # Too young
    res = schemes_checker.check_eligibility("Atal Pension Yojana", age=16)
    assert res["eligible"] == "false"
    
    # Too old
    res = schemes_checker.check_eligibility("Atal Pension Yojana", age=45)
    assert res["eligible"] == "false"
    
    # Eligible
    res = schemes_checker.check_eligibility("Atal Pension Yojana", age=30)
    assert res["eligible"] == "true"

def test_sukanya_samriddhi_eligibility():
    # Missing info
    res = schemes_checker.check_eligibility("Sukanya Samriddhi")
    assert res["eligible"] == "unknown"
    assert "has_girl_child" in res["missing_information"]
    
    # No girl child
    res = schemes_checker.check_eligibility("Sukanya Samriddhi", has_girl_child=False)
    assert res["eligible"] == "false"
    
    # Has girl child but age missing
    res = schemes_checker.check_eligibility("Sukanya Samriddhi", has_girl_child=True)
    assert res["eligible"] == "unknown"
    assert "girl_child_age" in res["missing_information"]
    
    # Girl child too old
    res = schemes_checker.check_eligibility("Sukanya Samriddhi", has_girl_child=True, girl_child_age=12)
    assert res["eligible"] == "false"
    
    # Eligible
    res = schemes_checker.check_eligibility("Sukanya Samriddhi", has_girl_child=True, girl_child_age=6)
    assert res["eligible"] == "true"

def test_pm_mudra_eligibility():
    # Missing age and purpose
    res = schemes_checker.check_eligibility("PM Mudra")
    assert res["eligible"] == "unknown"
    assert "age" in res["missing_information"]
    assert "purpose" in res["missing_information"]
    
    # Underage
    res = schemes_checker.check_eligibility("PM Mudra", age=16, purpose="business")
    assert res["eligible"] == "false"
    
    # Personal purpose
    res = schemes_checker.check_eligibility("PM Mudra", age=25, purpose="personal loan to buy car")
    assert res["eligible"] == "false"
    
    # Eligible
    res = schemes_checker.check_eligibility("PM Mudra", age=25, purpose="shop setup and inventory")
    assert res["eligible"] == "true"

def test_pmjjby_pmsby_eligibility():
    # PMJJBY (18-50)
    assert schemes_checker.check_eligibility("PMJJBY", age=17)["eligible"] == "false"
    assert schemes_checker.check_eligibility("PMJJBY", age=30)["eligible"] == "true"
    assert schemes_checker.check_eligibility("PMJJBY", age=55)["eligible"] == "false"
    
    # PMSBY (18-70)
    assert schemes_checker.check_eligibility("PMSBY", age=17)["eligible"] == "false"
    assert schemes_checker.check_eligibility("PMSBY", age=65)["eligible"] == "true"
    assert schemes_checker.check_eligibility("PMSBY", age=72)["eligible"] == "false"

def test_failure_simulation():
    # Set the environment variable
    os.environ["SIMULATE_ELIGIBILITY_FAILURE"] = "true"
    try:
        res = schemes_checker.check_eligibility("PM Mudra", age=25, purpose="business")
        assert res["eligible"] == "unknown"
        assert "error" in res
        assert res["error"] == "Data source unavailable"
        assert res["source"] == "N/A"
        assert res["verified_date"] == "N/A"
    finally:
        # Reset the environment variable
        os.environ["SIMULATE_ELIGIBILITY_FAILURE"] = "false"
