# Backend.py
import google.generativeai as genai
import json
from difflib import SequenceMatcher

import os

# Configure Gemini
from dotenv import load_dotenv

load_dotenv()  # Loads variables from .env into environment

import google.generativeai as genai

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not set in environment or .env file")
genai.configure(api_key=api_key)

def similar(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def process_dish_entry_json(dish_entry, food_data):
    dish_name = dish_entry["dish"]
    issues = dish_entry.get("issues", [])
    logs = []

    # Extract ingredients
    ingredients = get_ingredients_from_dish(dish_name, food_data)
    logs.append(f"Extracted ingredients using Gemini: {ingredients}")

    # Nutrition matching
    matched = match_ingredients_to_nutrition(ingredients, food_data)
    unmatched = [i for i in ingredients if not any(m['ingredient'] == i for m in matched)]
    for u in unmatched:
        logs.append(f"⚠️ No nutritional match found for '{u}' - likely missing in DB or spelling variation.")

    # Category classification
    category, weight = classify_dish_category(dish_name)
    if category == "Unknown":
        logs.append(f"⚠️ Could not classify dish, defaulted to 100g serving.")

    # Add any issues from the JSON
    for issue in issues:
        logs.append(f"⚠️ Issue from input: {issue}")

    # Nutrition calculation
    totals = {
        "energy_kj": 0, "energy_kcal": 0, "carb_g": 0, "protein_g": 0,
        "fat_g": 0, "freesugar_g": 0, "fibre_g": 0
    }
    for entry in matched:
        try:
            totals["energy_kj"] += float(entry.get("energy_kj", 0))
            totals["energy_kcal"] += float(entry.get("energy_kcal", 0))
            totals["carb_g"] += float(entry.get("carb_g", 0))
            totals["protein_g"] += float(entry.get("protein_g", 0))
            totals["fat_g"] += float(entry.get("fat_g", 0))
            totals["freesugar_g"] += float(entry.get("freesugar_g", 0))
            totals["fibre_g"] += float(entry.get("fibre_g", 0))
        except Exception:
            continue

    scale_factor = weight / 100
    scaled_nutrition = {k: round(v * scale_factor, 2) for k, v in totals.items()}

    return {
        "dish": dish_name,
        "ingredients_extracted": ingredients,
        "logs": logs,
        "category": category,
        "serving_weight_g": weight,
        "nutrition_per_serving": scaled_nutrition
    }


def convert_to_grams(quantity, unit, ingredient):
    DENSITY_MAP = {
        "oil": 13,        
        "sugar": 12.5,    
        "flour": 8,       
    }
    unit = unit.lower()
    ingredient = ingredient.lower()
    for key in DENSITY_MAP:
        if key in ingredient:
            grams_per_tbsp = DENSITY_MAP[key]
            break
    else:
        grams_per_tbsp = 10  

    if unit in ["tbsp", "tablespoon"]:
        return quantity * grams_per_tbsp
    elif unit in ["tsp", "teaspoon"]:
        return quantity * grams_per_tbsp / 3 
    elif unit in ["g", "gram", "grams"]:
        return quantity
    else:
        raise ValueError("Unknown unit")


def clean_ingredient_name(name):
    remove_words = ['fresh', 'dried', 'raw', 'cooked', 'boiled', 'fried', 'roasted']
    name = name.lower()
    for word in remove_words:
        name = name.replace(word, '').strip()
    return name

def load_data_from_file(filepath="data.txt"):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    
    data_lines = [line for line in lines if line and not line.startswith('|-')]
    
    entries = []
    for line in data_lines:
        parts = [part.strip() for part in line.split('|') if part.strip()]
        if len(parts) >= 8:  
            entry = {
                'food_name': parts[0],
                'energy_kj': parts[1],
                'energy_kcal': parts[2],
                'carb_g': parts[3],
                'protein_g': parts[4],
                'fat_g': parts[5],
                'freesugar_g': parts[6],
                'fibre_g': parts[7]
            }
            entries.append(entry)
    return entries

def get_common_ingredients(food_data):
    ingredients = []
    for item in food_data:
        try:
            name = item['food_name'].lower()
            base_name = name.split('(')[0].strip()
            ingredients.append(base_name)
        except KeyError:
            continue
    return list(set(ingredients)) 

def get_all_ingredients(food_data):
    return [item['food_name'].strip() for item in food_data]

def get_ingredients_from_dish(dish_name, food_data):
    model = genai.GenerativeModel("models/gemini-1.5-flash-latest")
    
    all_ingredients = get_all_ingredients(food_data)
    
    prompt = f"""You are an expert in Indian cuisine and nutrition.Your task is to identify the exact ingredients needed for the dish '{dish_name}' from this database of ingredients:

{json.dumps(all_ingredients, indent=2)}

Instructions:
1. Select ONLY ingredients that exist in the list above
2. Use the EXACT names as they appear in the list
3. List each ingredient on a new line starting with '-'
4. Only include main ingredients (no spices or seasonings unless specifically needed)
5. Do not include quantities or preparation steps

Example format:
- Rice, raw, milled (Oryza sativa)
- Wheat flour, atta (Triticum aestivum)
- Maize, tender, local (Zea mays)

Now list the exact ingredients from the database that would be used to make '{dish_name}':
important instruction - select only one of a kind , ie if the input dish is jeera aloo and there are multiple aloo in the list , imagine as a chef you have to complete the dish so just pick the ingredients from pantry that you need to complete the dish 

"""

    
    response = model.generate_content(prompt)
    return [line.strip("- ").strip() for line in response.text.split("\n") if line.strip()]

def match_ingredients_to_nutrition(ingredients, food_data):
    matched = []
    for ing in ingredients:
        best_match = None
        best_score = 0.8  
        
        for item in food_data:
            try:
                food_name = item['food_name']
                if ing.lower() == food_name.lower():
                    best_match = item
                    best_score = 1.0
                    break
                
                score = similar(ing, food_name)
                if score > best_score:
                    best_match = item
                    best_score = score
            except KeyError:
                continue
        
        if best_match:
            matched.append({
                "ingredient": ing,
                "matched_to": best_match['food_name'],
                "match_confidence": best_score,
                **best_match
            })
        else:
            print(f"⚠️ No match found for ingredient: {ing}")
    
    return matched

FOOD_CATEGORY_WEIGHTS = {
    "Dry Rice Item": 124,
    "Wet Rice Item": 150,
    "Veg Gravy": 150,
    "Veg Fry": 100,
    "Non - Veg Gravy": 150,
    "Non - Veg Fry": 100,
    "Dals": 150,
    "Wet Breakfast Item": 130,
    "Dry Breakfast Item": 100,
    "Chutneys": 15,
    "Plain Flatbreads": 50,
    "Stuffed Flatbreads": 100,
    "Salads": 100,
    "Raita": 150,
    "Plain Soups": 150,
    "Mixed Soups": 250,
    "Hot Beverages": 250,
    "Beverages": 250,
    "Snacks": 100,
    "Sweets": 120,
}


CATEGORY_SERVING_DESC = {
    "Dry Rice Item": "1 small bowl (~124g)",
    "Wet Rice Item": "1 medium katori (~150g)",
    "Veg Gravy": "1 medium katori (~150g)",
    "Veg Fry": "1 small bowl (~100g)",
    "Non - Veg Gravy": "1 medium katori (~150g)",
    "Non - Veg Fry": "1 small bowl (~100g)",
    "Dals": "1 medium katori (~150g)",
    "Wet Breakfast Item": "1 medium plate (~130g)",
    "Dry Breakfast Item": "1 serving (~100g)",
    "Chutneys": "2 tbsp (~15g)",
    "Plain Flatbreads": "1 piece (~50g)",
    "Stuffed Flatbreads": "1 piece (~100g)",
    "Salads": "1 serving (~100g)",
    "Raita": "1 medium bowl (~150g)",
    "Plain Soups": "1 medium bowl (~150g)",
    "Mixed Soups": "1 full bowl (~250g)",
    "Hot Beverages": "1 cup (~250g)",
    "Beverages": "1 glass (~250g)",
    "Snacks": "1 serving (~100g)",
    "Sweets": "1 piece (~120g)"
}


def display_nutrition_info(nutrition_dict, serving_weight, category):
    serving_desc = CATEGORY_SERVING_DESC.get(category, f"~{serving_weight}g")
    print(f"\n🥄 Estimated Nutrition per 1 serving ({serving_desc}):")
    print("| Nutrient        | Amount             |")
    print("|----------------|--------------------|")
    print("| 🔥 Energy       | {:.2f} kcal ({:.2f} kJ) |".format(
        nutrition_dict["energy_kcal"], nutrition_dict["energy_kj"]))
    print("| 🍚 Carbohydrates | {:.2f} g            |".format(nutrition_dict["carb_g"]))
    print("| 🍗 Protein       | {:.2f} g            |".format(nutrition_dict["protein_g"]))
    print("| 🧈 Fat           | {:.2f} g            |".format(nutrition_dict["fat_g"]))
    print("| 🍬 Free Sugar    | {:.2f} g            |".format(nutrition_dict["freesugar_g"]))
    print("| 🌾 Fibre         | {:.2f} g            |".format(nutrition_dict["fibre_g"]))

def classify_dish_category(dish_name):
    prompt = f"""
Given this list of food categories:
{list(FOOD_CATEGORY_WEIGHTS.keys())}

Which one best describes the Indian dish '{dish_name}'?

Only return the exact matching category name.
"""
    model = genai.GenerativeModel("models/gemini-1.5-flash-latest")
    response = model.generate_content(prompt)
    category = response.text.strip()
    if category not in FOOD_CATEGORY_WEIGHTS:
        print("⚠️ Unable to classify dish. Defaulting to 100g.")
        return "Unknown", 100
    return category, FOOD_CATEGORY_WEIGHTS[category]


def process_dish_entry(dish_entry, food_data):
    dish_name = dish_entry["dish"]
    issues = dish_entry["issues"]
    log = []

    print(f"\n🍽️ Processing Dish: {dish_name}")
    
    ingredients = get_ingredients_from_dish(dish_name, food_data)
    log.append(f"Extracted ingredients using Gemini: {ingredients}")
    
    matched = match_ingredients_to_nutrition(ingredients, food_data)
    unmatched = [i for i in ingredients if not any(m['ingredient'] == i for m in matched)]
    
    for u in unmatched:
        log.append(f"⚠️ No nutritional match found for '{u}' — likely missing in DB or spelling variation.")
    
    category, weight = classify_dish_category(dish_name)
    if category == "Unknown":
        log.append(f"⚠️ Could not classify dish, defaulted to 100g serving.")

    print("\n📝 Assumptions & Logs:")
    for l in log:
        print(f"- {l}")


def process_dish_entry_streamlit(dish_entry, food_data):
    dish_name = dish_entry.get("dish", "")
    issues = dish_entry.get("issues", [])
    log = []

    log.append(f"🍽️ Processing Dish: {dish_name}")

    ingredients = get_ingredients_from_dish(dish_name, food_data)
    log.append(f"Extracted ingredients using Gemini: {ingredients}")

    matched = match_ingredients_to_nutrition(ingredients, food_data)
    unmatched = [i for i in ingredients if not any(m['ingredient'] == i for m in matched)]
    for u in unmatched:
        log.append(f"⚠️ No nutritional match found for '{u}' - likely missing in DB or spelling variation.")

    category, weight = classify_dish_category(dish_name)
    if category == "Unknown":
        log.append(f"⚠️ Could not classify dish, defaulted to 100g serving.")

    for issue in issues:
        log.append(f"⚠️ Issue from input: {issue}")

    totals = {
        "energy_kj":0, "energy_kcal": 0, "carb_g": 0, "protein_g": 0,
        "fat_g": 0, "freesugar_g": 0, "fibre_g": 0
    }
    for entry in matched:
        try:
            totals["energy_kj"] += float(entry.get("energy_kj", 0))
            totals["energy_kcal"] += float(entry.get("energy_kcal", 0))
            totals["carb_g"] += float(entry.get("carb_g", 0))
            totals["protein_g"] += float(entry.get("protein_g", 0))
            totals["fat_g"] += float(entry.get("fat_g", 0))
            totals["freesugar_g"] += float(entry.get("freesugar_g", 0))
            totals["fibre_g"] += float(entry.get("fibre_g", 0))
        except Exception:
            continue

    scale_factor = weight / 100
    scaled_nutrition = {k: round(v * scale_factor, 2) for k, v in totals.items()}

    return {
        "dish": dish_name,
        "log": log,
        "ingredients": ingredients,
        "matched": matched,
        "unmatched": unmatched,
        "category": category,
        "serving_weight": weight,
        "nutrition_per_serving": scaled_nutrition,
        "issues": issues,
    }

def calculate_totals(matched, serving_weight):
    totals = {k: 0 for k in ["energy_kj", "energy_kcal", "carb_g", 
                            "protein_g", "fat_g", "freesugar_g", "fibre_g"]}
    for entry in matched:
        for k in totals:
            try:
                totals[k] += float(entry[k])
            except (KeyError, ValueError):
                continue
    
    scale_factor = serving_weight / 100
    return {k: round(v * scale_factor, 2) for k, v in totals.items()}