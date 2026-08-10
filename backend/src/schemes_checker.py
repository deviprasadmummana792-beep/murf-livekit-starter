import os
import json
import logging
from pathlib import Path

logger = logging.getLogger("schemes_checker")

DATA_FILE_PATH = Path(__file__).parent / "schemes_data.json"

def match_scheme(name: str) -> str | None:
    if not name:
        return None
    name_lower = name.lower()
    if "mudra" in name_lower:
        return "pm_mudra"
    if "jan dhan" in name_lower or "pmjdy" in name_lower or "jandhan" in name_lower:
        return "pm_jan_dhan"
    if "sukanya" in name_lower or "ssy" in name_lower:
        return "sukanya_samriddhi"
    if "atal" in name_lower or "apy" in name_lower or "pension" in name_lower:
        return "atal_pension"
    if "kisan" in name_lower or "pmkisan" in name_lower:
        return "pm_kisan"
    if "pmjjby" in name_lower or "jeevan jyoti" in name_lower:
        return "pmjjby"
    if "pmsby" in name_lower or "suraksha bima" in name_lower:
        return "pmsby"
    return None

def check_eligibility(
    scheme_name: str,
    age: int | None = None,
    occupation: str | None = None,
    income_range: str | None = None,
    purpose: str | None = None,
    is_farmer: bool | None = None,
    has_girl_child: bool | None = None,
    girl_child_age: int | None = None,
) -> dict:
    simulate_fail = os.environ.get("SIMULATE_ELIGIBILITY_FAILURE", "false").lower() == "true"
    
    scheme_id = match_scheme(scheme_name)
    
    logger.info("[TOOL] check_scheme_eligibility called")
    logger.info("[TOOL] scheme: %s", scheme_name)
    
    if simulate_fail:
        # Simulate data source failure
        logger.info("[TOOL] result: unknown")
        logger.info("[TOOL] source: N/A")
        logger.info("[TOOL] verified_date: N/A")
        logger.info("[TOOL] failure: Simulated data source failure")
        return {
            "scheme": scheme_name,
            "eligible": "unknown",
            "reasons": ["Data source unavailable. Simulated failure mode."],
            "missing_information": [],
            "source": "N/A",
            "verified_date": "N/A",
            "error": "Data source unavailable"
        }
        
    try:
        if not DATA_FILE_PATH.exists():
            raise FileNotFoundError(f"Scheme dataset not found at {DATA_FILE_PATH}")
        with open(DATA_FILE_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.info("[TOOL] result: unknown")
        logger.info("[TOOL] source: N/A")
        logger.info("[TOOL] verified_date: N/A")
        logger.info("[TOOL] failure: %s", str(e))
        return {
            "scheme": scheme_name,
            "eligible": "unknown",
            "reasons": [f"Could not load local database: {str(e)}"],
            "missing_information": [],
            "source": "N/A",
            "verified_date": "N/A",
            "error": "Data source unavailable"
        }

    if not scheme_id or scheme_id not in data:
        logger.info("[TOOL] result: unknown")
        logger.info("[TOOL] source: N/A")
        logger.info("[TOOL] verified_date: N/A")
        logger.info("[TOOL] failure: Scheme not found in local dataset")
        return {
            "scheme": scheme_name,
            "eligible": "unknown",
            "reasons": [f"Scheme '{scheme_name}' is not in the local database."],
            "missing_information": [],
            "source": "N/A",
            "verified_date": "N/A"
        }

    scheme_info = data[scheme_id]
    rules = scheme_info["rules"]
    source = scheme_info["source"]
    verified_date = scheme_info["verified_date"]
    name_display = scheme_info["name"]

    eligible = "unknown"
    reasons = []
    missing_info = []

    # PM Jan Dhan
    if scheme_id == "pm_jan_dhan":
        if age is None:
            missing_info.append("age")
            reasons.append("Age is required to check PM Jan Dhan Yojana eligibility.")
        else:
            try:
                age_val = int(age)
                if age_val >= rules["min_age"]:
                    eligible = "true"
                    reasons.append(f"Applicant age is {age_val}, which is greater than or equal to the minimum required age of {rules['min_age']}.")
                else:
                    eligible = "false"
                    reasons.append(f"Applicant age is {age_val}, which is less than the minimum required age of {rules['min_age']}.")
            except ValueError:
                eligible = "unknown"
                reasons.append("Provided age is invalid.")

    # PM Kisan
    elif scheme_id == "pm_kisan":
        farmer_flag = is_farmer
        if farmer_flag is None and occupation:
            occ_lower = occupation.lower()
            if "farmer" in occ_lower or "farming" in occ_lower or "kisan" in occ_lower:
                farmer_flag = True
                reasons.append("Inferred farmer status from occupation.")
            elif any(x in occ_lower for x in ["student", "teacher", "clerk", "doctor", "engineer", "software"]):
                farmer_flag = False
                reasons.append("Inferred non-farmer status from occupation.")

        if farmer_flag is None:
            missing_info.append("is_farmer")
            reasons.append("Farmer status (landholding status) is required to check PM-KISAN eligibility.")
        elif farmer_flag is True:
            eligible = "true"
            reasons.append("Applicant is a landholding farmer.")
        else:
            eligible = "false"
            reasons.append("PM-KISAN is specifically for landholding farmer families.")

    # APY
    elif scheme_id == "atal_pension":
        if age is None:
            missing_info.append("age")
            reasons.append("Age is required to check Atal Pension Yojana eligibility.")
        else:
            try:
                age_val = int(age)
                if rules["min_age"] <= age_val <= rules["max_age"]:
                    eligible = "true"
                    reasons.append(f"Applicant age {age_val} is within the required range of {rules['min_age']} to {rules['max_age']} years.")
                else:
                    eligible = "false"
                    reasons.append(f"Applicant age {age_val} is outside the required range of {rules['min_age']} to {rules['max_age']} years.")
            except ValueError:
                eligible = "unknown"
                reasons.append("Provided age is invalid.")

    # SSY
    elif scheme_id == "sukanya_samriddhi":
        if has_girl_child is None:
            missing_info.append("has_girl_child")
            reasons.append("Need to know if you have a girl child to check Sukanya Samriddhi eligibility.")
        elif has_girl_child is False:
            eligible = "false"
            reasons.append("Sukanya Samriddhi Yojana requires a girl child.")
        else:
            if girl_child_age is None:
                missing_info.append("girl_child_age")
                reasons.append("Girl child's age is required to verify Sukanya Samriddhi Yojana eligibility.")
            else:
                try:
                    gc_age_val = int(girl_child_age)
                    if gc_age_val <= rules["max_girl_child_age"]:
                        eligible = "true"
                        reasons.append(f"Girl child age {gc_age_val} is within the allowed limit of {rules['max_girl_child_age']} years.")
                    else:
                        eligible = "false"
                        reasons.append(f"Girl child age {gc_age_val} exceeds the maximum allowed age of {rules['max_girl_child_age']} years.")
                except ValueError:
                    eligible = "unknown"
                    reasons.append("Provided girl child age is invalid.")

    # PM Mudra
    elif scheme_id == "pm_mudra":
        age_ok = None
        if age is None:
            missing_info.append("age")
            reasons.append("Age is required to check PM Mudra Loan eligibility.")
        else:
            try:
                age_val = int(age)
                if age_val >= rules["min_age"]:
                    age_ok = True
                else:
                    age_ok = False
                    reasons.append(f"Applicant age {age_val} is below the minimum required age of {rules['min_age']} for PM Mudra Loan.")
            except ValueError:
                reasons.append("Provided age is invalid.")
                age_ok = False

        purpose_ok = None
        if purpose is None:
            missing_info.append("purpose")
            reasons.append("The purpose of the loan (business/commercial vs personal) is required to check PM Mudra Loan eligibility.")
        else:
            p_lower = purpose.lower()
            if any(k in p_lower for k in ["personal", "home", "car", "education", "marriage", "wedding", "vacation"]):
                purpose_ok = False
                reasons.append("PM Mudra Loan is only for business, commercial, or micro-enterprise purposes, not for personal use.")
            else:
                purpose_ok = True
                reasons.append(f"Loan purpose '{purpose}' matches commercial/business use criteria.")

        if age_ok is False or purpose_ok is False:
            eligible = "false"
        elif age_ok is True and purpose_ok is True:
            eligible = "true"
            reasons.append("Applicant meets age and business purpose criteria for PM Mudra Loan.")
        else:
            eligible = "unknown"

    # PMJJBY
    elif scheme_id == "pmjjby":
        if age is None:
            missing_info.append("age")
            reasons.append("Age is required to check PMJJBY eligibility.")
        else:
            try:
                age_val = int(age)
                if rules["min_age"] <= age_val <= rules["max_age"]:
                    eligible = "true"
                    reasons.append(f"Applicant age {age_val} is within the required range of {rules['min_age']} to {rules['max_age']} years.")
                else:
                    eligible = "false"
                    reasons.append(f"Applicant age {age_val} is outside the required range of {rules['min_age']} to {rules['max_age']} years.")
            except ValueError:
                eligible = "unknown"
                reasons.append("Provided age is invalid.")

    # PMSBY
    elif scheme_id == "pmsby":
        if age is None:
            missing_info.append("age")
            reasons.append("Age is required to check PMSBY eligibility.")
        else:
            try:
                age_val = int(age)
                if rules["min_age"] <= age_val <= rules["max_age"]:
                    eligible = "true"
                    reasons.append(f"Applicant age {age_val} is within the required range of {rules['min_age']} to {rules['max_age']} years.")
                else:
                    eligible = "false"
                    reasons.append(f"Applicant age {age_val} is outside the required range of {rules['min_age']} to {rules['max_age']} years.")
            except ValueError:
                eligible = "unknown"
                reasons.append("Provided age is invalid.")

    logger.info("[TOOL] result: %s", eligible)
    logger.info("[TOOL] source: %s", source)
    logger.info("[TOOL] verified_date: %s", verified_date)
    logger.info("[TOOL] failure: None")

    return {
        "scheme": name_display,
        "eligible": eligible,
        "reasons": reasons,
        "missing_information": missing_info,
        "source": source,
        "verified_date": verified_date
    }
