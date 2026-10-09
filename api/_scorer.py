import re

# (pattern, weight, reason)
RULES = [
    (r"\b(otp|one[- ]time password|verification code)\b", 30, "Asks for OTP/code"),
    (r"\b(cvv|pin|card number|account number|password)\b", 30, "Asks for sensitive credentials"),
    (r"\b(arrest|police|cbi|customs|legal action|warrant|court)\b", 25, "Threat / authority impersonation"),
    (r"\b(urgent|immediately|right now|last chance|within \d+ (minutes|hours))\b", 15, "Urgency pressure"),
    (r"\b(gift card|crypto|bitcoin|wire transfer|western union|upi)\b", 20, "Unusual payment method"),
    (r"\b(your account (is|has been) (blocked|suspended|compromised))\b", 20, "Account-threat claim"),
    (r"\b(kyc|refund|lottery|prize|winner)\b", 15, "Common scam hook"),
    (r"\b(don'?t tell anyone|keep this secret|do not disconnect)\b", 25, "Isolation tactic"),
    (r"\b(anydesk|teamviewer|install (an )?app)\b", 25, "Remote-access request"),
]


def score_text(text: str):
    text = text.lower()
    total, reasons = 0, []
    for pattern, weight, reason in RULES:
        if re.search(pattern, text):
            total += weight
            reasons.append(reason)
    total = min(total, 100)
    level = "HIGH" if total >= 60 else "MEDIUM" if total >= 30 else "LOW"
    return total, level, reasons
