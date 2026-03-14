def classify_bmi(bmi):
    """
    Classifies fitness status based on BMI (WHO-aligned thresholds).
    Returns a safe dummy classification on invalid input.
    """
    try:
        b = float(bmi)
    except (TypeError, ValueError):
        return "Normal"  # dummy fallback
    if b < 18.5:
        return "Underweight"
    elif 18.5 <= b < 25:
        return "Normal"
    elif 25 <= b < 30:
        return "Overweight"
    else:
        return "Obese"

_recommendation_cache = {}

def generate_recommendations(status, student_profile=None):
    """
    Generates health and exercise recommendations.
    Uses dummy/placeholder response on any error so the pipeline never fails.

    student_profile (optional dict) may include:
      - age: int
      - gender: str
      - test_scores: dict (e.g., {"Stamina": 40, "Strength": 70})
      - previous_test_scores: dict (same shape as test_scores)
      - recent_performances: list of dicts (e.g., [{"metric_name": "Stamina", "score": 40}, ...])
    """
    _dummy_response = (
        "Maintain a healthy lifestyle with balanced diet and regular physical activity. "
        "Consult your teacher or healthcare provider for personalized advice."
    )
    try:
        return _generate_recommendations_impl(status, student_profile)
    except Exception:
        return _dummy_response


def _generate_recommendations_impl(status, student_profile=None):
    # Keep legacy caching only for the generic (no-profile) case.
    if not student_profile and status in _recommendation_cache:
        return _recommendation_cache[status]

    profile = student_profile or {}
    age = profile.get('age')
    gender = profile.get('gender')

    def _to_float(v):
        try:
            if v is None:
                return None
            return float(v)
        except (TypeError, ValueError):
            return None

    def _normalize_key(k: str) -> str:
        return str(k).strip().lower().replace('_', ' ')

    def _merge_scores() -> dict:
        scores = {}

        for src in (profile.get('previous_test_scores') or {}, profile.get('test_scores') or {}):
            if isinstance(src, dict):
                for k, v in src.items():
                    scores[_normalize_key(k)] = _to_float(v)

        recent = profile.get('recent_performances') or []
        if isinstance(recent, list):
            for item in recent:
                if not isinstance(item, dict):
                    continue
                k = item.get('metric_name')
                v = item.get('score')
                if k is None:
                    continue
                scores[_normalize_key(k)] = _to_float(v)

        return scores

    scores = _merge_scores()

    def _score_for(*keys):
        for k in keys:
            v = scores.get(_normalize_key(k))
            if v is not None:
                return v
        return None

    stamina = _score_for('stamina', 'endurance', 'cardio', 'aerobic')
    strength = _score_for('strength', 'power')
    flexibility = _score_for('flexibility', 'mobility')

    # Heuristic thresholds (0-100). If your scoring system differs, adjust these.
    low_threshold = 45
    high_threshold = 75

    is_low_stamina = stamina is not None and stamina < low_threshold
    is_low_strength = strength is not None and strength < low_threshold
    is_low_flex = flexibility is not None and flexibility < low_threshold

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

    base = recommendations.get(status, "Maintain a healthy lifestyle and stay active.")

    # If no profile signals are available, return the generic template.
    if not student_profile:
        _recommendation_cache[status] = base
        return base

    extras = []

    # Age tailoring (light-touch; avoid medical claims).
    if isinstance(age, int) and age > 0:
        if age < 13:
            extras.append(
                "For this age group, keep sessions playful: short intervals of activity with breaks, focusing on consistency."
            )
        elif age < 18:
            extras.append(
                "Aim for a weekly routine with gradual progression (avoid sudden spikes in intensity)."
            )
        else:
            extras.append(
                "Progress gradually and prioritize recovery days alongside training."
            )

    if isinstance(gender, str) and gender.strip():
        # Keep neutral language; gender may not meaningfully change safe recommendations.
        extras.append("Recommendations are suitable regardless of gender; focus on safe progression and consistency.")

    # Status + performance-driven specificity.
    if status in ("Overweight", "Obese"):
        if is_low_stamina:
            extras.append(
                "Because stamina/endurance appears low, start with low-impact cardio 4x/week: brisk walking, cycling, or swimming for 15–25 minutes, then increase by 5 minutes per week."
            )
            extras.append(
                "Add 1–2 interval sessions/week: 30 seconds faster pace + 90 seconds easy pace repeated 6–8 times."
            )
        else:
            extras.append(
                "Include steady-state cardio 3–5x/week (20–40 minutes) and track progress with time or distance goals."
            )

        if is_low_strength:
            extras.append(
                "Add full-body strength work 2–3x/week (squats, lunges, push-ups, rows) to support healthy body composition."
            )

    if status == "Underweight":
        if is_low_strength:
            extras.append(
                "Strength score looks low—prioritize progressive resistance training 3x/week with adequate rest and nutrition."
            )
        if is_low_stamina:
            extras.append(
                "Keep cardio light-to-moderate initially; avoid excessive calorie burn until weight goals are met."
            )

    if status == "Normal":
        if stamina is not None and stamina >= high_threshold:
            extras.append(
                "Stamina looks strong—maintain with 1–2 longer sessions/week and 1 interval session/week."
            )
        if is_low_flex:
            extras.append(
                "Flexibility/mobility seems low—add 8–10 minutes of stretching or mobility drills after workouts (hips, hamstrings, shoulders)."
            )

    # Include a compact summary of detected weak areas.
    weak_areas = []
    if is_low_stamina:
        weak_areas.append('stamina')
    if is_low_strength:
        weak_areas.append('strength')
    if is_low_flex:
        weak_areas.append('flexibility')
    if weak_areas:
        extras.insert(0, f"Focus areas based on recent scores: {', '.join(weak_areas)}.")

    result = base + " " + " ".join(extras) if extras else base
    return result

