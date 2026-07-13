import datetime
from typing import Dict, List, Any

def evaluate_screening(responses: Dict[str, str], beneficiary_id: str, screened_by: str) -> Dict[str, Any]:
    """Evaluates SDoH/HRSN responses and returns flagged domains.

    Args:
        responses (Dict[str, str]): Key-value pairs of the screening responses.
        beneficiary_id (str): The ID of the beneficiary.
        screened_by (str): The user ID of the staff member who conducted the screening.

    Returns:
        Dict[str, Any]: Structured evaluation containing beneficiary_id, flags list, timestamp, and screened_by.
    """
    flags = []

    # 1. Housing flag: Concern is "Yes" OR Stability is "No" or "Unsure"
    housing_concern = responses.get("housing_concern")
    housing_stability = responses.get("housing_stability")
    if housing_concern == "Yes" or housing_stability in ["No", "Unsure"]:
        flags.append("Housing")

    # 2. Food flag: Security is "Often true" or "Sometimes true"
    food_security = responses.get("food_security")
    if food_security in ["Often true", "Sometimes true"]:
        flags.append("Food")

    # 3. Transportation flag: Transportation is "Yes"
    transportation = responses.get("transportation")
    if transportation == "Yes":
        flags.append("Transportation")

    # 4. Utilities flag: Utilities is "Yes" or "Already shut off"
    utilities = responses.get("utilities")
    if utilities in ["Yes", "Already shut off"]:
        flags.append("Utilities")

    # 5. Safety flag: Safety is "Yes"
    safety = responses.get("safety")
    if safety == "Yes":
        flags.append("Safety")

    return {
        "beneficiary_id": beneficiary_id,
        "flags": flags,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "screened_by": screened_by
    }
