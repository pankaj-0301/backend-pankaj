# 🧠 VYB AI - Smart Nutrition Estimator

A resilient nutrition estimation system built in **Python** that estimates nutritional values of **home-cooked Indian meals** — even with **partial, messy, or ambiguous data**.

---

## 🚀 Goal

> Given a **dish name**, return **per-serving nutrition** (e.g., per 1 katori) using real-world data, household measurements, and reasoning — even if ingredient data is incomplete or dish names are vague.

---

## 🔧 Features

- ✅ LLM-powered ingredient extraction using **Gemini 1.5 Flash**
- ✅ Ingredient ↔ nutrition mapping with fuzzy matching
- ✅ Custom unit-to-gram converter using **ingredient-specific density**
- ✅ Handles missing data, synonyms, spelling variations, and messy inputs
- ✅ Returns nutrition estimates for **standard household portions**
- ✅ Modular design and clean logging of all assumptions and fallbacks

---

## 🛠️ How It Works

### 📥 Input
Dish name (e.g., `Paneer Butter Masala`)

### 🧬 Processing Pipeline

1. **LLM Ingredient Extraction**
   - Uses Gemini Flash 1.5 to extract only valid ingredients from a known DB
   - Filters out spices and focuses on core items

2. **Clean and Normalize Ingredients**
   - Lowercased, normalized (e.g., removes "roasted", "fried")

3. **Ingredient Matching**
   - Uses fuzzy string similarity to match with closest nutrition DB entry
   - If no match ≥ 80%, logs a fallback warning

4. **Quantity Conversion**
   - Converts units like `tbsp`, `glass`, etc. to grams
   - Applies custom density per ingredient

5. **Nutrition Calculation**
   - Scales per 100g nutrition to estimated gram quantity
   - Aggregates per ingredient

6. **Portion Scaling**
   - Converts total dish nutrition to **per 1 katori** (~150g standard) based on category

7. **Logging**
   - Logs all assumptions, errors, and fallbacks in `debug-log.txt`

---

## 🧪 Edge Case Handling

| Dish | Issue | Handling |
|------|-------|----------|
| Jeera Aloo (mild fried) | Ingredient synonym, no quantity | Picks best match using similarity, uses avg qty |
| Gobhi Sabzi | Ambiguous dish type | Assumes default category: Veg Gravy |
| Chana Masala | Missing nutrition entry | Logs missing item, ignores or estimates |
| Paneer Curry with capsicum | Unit in “glass”, spelling variation | Estimates grams from context |
| Mixed veg | No fixed recipe | Uses Gemini to guess ingredients, logs uncertainty |

---

## 🧠 Manual Reasoning Example

### Q: "Map 'lightly roasted jeera powder' to a nutrition entry. Why?"

**A:** Mapped to `Cumin seed, dried` because:
- Jeera = cumin (synonym)
- Roasting doesn’t significantly change macronutrient profile
- “Powder” implies processing, not composition change

---

### Q: Dish weight = 700g cooked, raw = 950g

**Loss Ratio =** (950 - 700) / 950 = **~26.3%**

If total nutrition was for 700g → adjust to 180g:

```python
scaled_nutrition = (180 / 700) * total_nutrition
