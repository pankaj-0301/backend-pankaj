from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
import os

# Import your existing backend functions
from Backend import (
    load_data_from_file,
    get_ingredients_from_dish,
    match_ingredients_to_nutrition,
    classify_dish_category,
    calculate_totals,
    process_dish_entry_json
)

app = FastAPI(title="Smart Nutrition Estimator API")

# Add CORS middleware to allow requests from the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load nutrition data at startup
food_data = load_data_from_file("data.txt")

class DishRequest(BaseModel):
    dish_name: str

class DishEntryRequest(BaseModel):
    dish: str
    issues: Optional[List[str]] = []

class DishEntriesRequest(BaseModel):
    entries: List[DishEntryRequest]

@app.get("/")
def read_root():
    return {"message": "Smart Nutrition Estimator API is running"}

@app.post("/analyze-dish")
def analyze_dish(request: DishRequest):
    try:
        # Get dish ingredients
        ingredients = get_ingredients_from_dish(request.dish_name, food_data)
        
        if not ingredients:
            return {"error": "No ingredients found for this dish"}
        
        # Match ingredients to nutrition data
        matched = match_ingredients_to_nutrition(ingredients, food_data)
        
        # Classify dish and get serving weight
        category, serving_weight = classify_dish_category(request.dish_name)
        
        # Calculate nutrition totals
        totals = calculate_totals(matched, serving_weight)
        
        # Return results
        return {
    "dish": request.dish_name,  # ✅ was dish_name
    "ingredients_extracted": ingredients,  # ✅ was ingredients
    "logs": [f"⚠️ {i} not matched" for i in ingredients if not any(m['ingredient'] == i for m in matched)],  # add logs
    "category": category,
    "serving_weight_g": serving_weight,
    "nutrition_per_serving": totals
}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze-json")
def process_json_data(request: DishEntriesRequest):
    try:
        results = []
        for entry in request.entries:
            dish_entry = {
                "dish": entry.dish,
                "issues": entry.issues or []
            }
            result = process_dish_entry_json(dish_entry, food_data)
            results.append(result)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# For testing purposes
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)