# Test Configuration for Voice Feedback Agent

## Testing Scenarios

### Scenario 1: Happy Path
Test with positive responses:
```
User: "Haan bilkul"
User: "5"
User: "Haan"
User: "5"
User: "Haan"
User: "Bahut achhi service thi, thank you"
```

Expected JSON:
```json
{
  "q1_overall_rating_1to5": 5,
  "q2_washing_yesno": "yes",
  "q3_advisor_behavior_1to5": 5,
  "q4_promised_time_yesno": "yes",
  "q5_additional_comments_text": "Bahut achhi service thi, thank you"
}
```

### Scenario 2: Mixed Feedback
```
User: "Yes"
User: "Teen" (3)
User: "Nahi"
User: "Chaar" (4)
User: "Haan"
User: "Advisor thoda rude tha"
```

Expected JSON:
```json
{
  "q1_overall_rating_1to5": 3,
  "q2_washing_yesno": "no",
  "q3_advisor_behavior_1to5": 4,
  "q4_promised_time_yesno": "yes",
  "q5_additional_comments_text": "Advisor thoda rude tha"
}
```

### Scenario 3: User Declines
```
User: "Nahi, abhi busy hoon"
```

Agent should:
- Say farewell
- Save transcript
- Exit gracefully

## Voice Testing Tips

1. **Speak clearly** - Hinglish works best with clear pronunciation
2. **Use natural language** - Mix Hindi and English freely
3. **Wait for response** - Let Riya finish speaking before answering
4. **Be concise** - Short answers work better (e.g., "paanch" vs long sentences)

## Common Hinglish Phrases Understood

### Numbers (Ratings)
- 1: "ek", "one", "1"
- 2: "do", "two", "2"
- 3: "teen", "three", "3"
- 4: "chaar", "four", "4"
- 5: "paanch", "five", "5"

### Yes/No
- Yes: "haan", "ha", "yes", "bilkul", "ji", "theek hai"
- No: "nahi", "nai", "no", "na"

### Comments
- "Sab achha tha" (Everything was good)
- "Kuch nahi" (Nothing)
- "Bahut achhi service" (Very good service)
- "Time zyada laga" (Took too much time)
