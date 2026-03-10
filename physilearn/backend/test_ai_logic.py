import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "physilearn_backend.settings")
django.setup()

from api.ai_logic import classify_bmi, generate_recommendations

overall_status = "PASS"

def print_result(condition, test_name):
    global overall_status
    if condition:
        print(f"PASS: {test_name}")
    else:
        print(f"FAIL: {test_name}")
        overall_status = "FAIL"

test_cases = [
    {
        "category": "Underweight",
        "height_m": 1.70,
        "weight_kg": 50, # BMI: 50 / 2.89 = 17.3
        "expected_keyword": "nutrient-dense foods"
    },
    {
        "category": "Normal",
        "height_m": 1.70,
        "weight_kg": 65, # BMI: 65 / 2.89 = 22.49
        "expected_keyword": "active lifestyle"
    },
    {
        "category": "Overweight",
        "height_m": 1.70,
        "weight_kg": 80, # BMI: 80 / 2.89 = 27.68
        "expected_keyword": "cardiovascular exercises"
    }
]

for tc in test_cases:
    bmi = tc["weight_kg"] / (tc["height_m"] ** 2)
    status = classify_bmi(bmi)
    rec = generate_recommendations(status)
    
    print(f"\nTesting {tc['category']} Scenario:")
    print(f"  Calculated BMI: {bmi:.2f}")
    print(f"  Classified Status: {status}")
    print(f"  Recommendation Snippet: {rec[:50]}...")
    
    print_result(status == tc["category"], f"Correctly classified as {tc['category']}")
    print_result(tc["expected_keyword"] in rec, f"Recommendation corresponds to {tc['category']} (contains '{tc['expected_keyword']}')")

print(f"\nFINAL VERIFICATION: {overall_status}")
