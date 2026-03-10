def classify_bmi(bmi):
    """
    Classifies fitness status based on BMI.
    """
    if bmi < 18.5:
        return "Underweight"
    elif 18.5 <= bmi < 25:
        return "Normal"
    elif 25 <= bmi < 30:
        return "Overweight"
    else:
        return "Obese"

_recommendation_cache = {}

def generate_recommendations(status, student_profile=None):
    """
    Generates personalized health and exercise recommendations with basic caching.
    """
    if status in _recommendation_cache:
        return _recommendation_cache[status]

    recommendations = {
        "Underweight": (
            "Focus on nutrient-dense foods and strength training. "
            "Ensure adequate protein intake and regular physical activity to build muscle mass."
        ),
        "Normal": (
            "Maintain your current balanced diet and active lifestyle. "
            "Incorporate a mix of aerobic exercises and strength training for overall fitness."
        ),
        "Overweight": (
            "Incorporate more cardiovascular exercises (e.g., swimming, cycling). "
            "Focus on portion control and reducing sugary snacks. Stay hydrated."
        ),
        "Obese": (
            "Consult with a specialist for a tailored weight management plan. "
            "Start with low-impact activities like walking and gradually increase intensity."
        )
    }
    result = recommendations.get(status, "Maintain a healthy lifestyle and stay active.")
    _recommendation_cache[status] = result
    return result

