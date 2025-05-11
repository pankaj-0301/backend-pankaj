import streamlit as st
import json

import json
from Backend import (
        load_data_from_file,
       get_ingredients_from_dish,
    match_ingredients_to_nutrition,
    classify_dish_category,
    calculate_totals,
    process_dish_entry_streamlit,

)

# Initialize nutrition data
@st.cache_resource
def load_food_data():
    return load_data_from_file("data.txt")

food_data = load_food_data()

# --- Streamlit UI ---
st.title("🍽️ Smart Nutrition Estimator")

mode = st.radio("Choose input method:", 
               ["🔍 Dish Name Lookup", "📋 JSON Data Input"],
               index=0)

if mode == "🔍 Dish Name Lookup":
    dish_name = st.text_input("Enter Indian dish name:", 
                             placeholder="Butter Chicken, Paneer Tikka...")
    
    if st.button("Calculate Nutrition"):
        if not dish_name:
            st.warning("Please enter a dish name")
        else:
            with st.spinner("🔍 Analyzing ingredients..."):
                ingredients = get_ingredients_from_dish(dish_name, food_data)
            
            if not ingredients:
                st.error("No ingredients found for this dish")
            else:
                st.subheader("Identified Ingredients")
                st.write(", ".join(ingredients))
                
                with st.spinner("📊 Calculating nutrition..."):
                    matched = match_ingredients_to_nutrition(ingredients, food_data)
                    category, serving_weight = classify_dish_category(dish_name)
                
                st.subheader("Nutrition Matches")
                for item in matched:
                    with st.expander(f"{item['ingredient']}"):
                        st.json(item)
                
                totals = calculate_totals(matched, serving_weight)
                
                st.subheader("📈 Per Serving Nutrition")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Category", f"{category} ({serving_weight}g)")
                with col2:
                    st.metric("Total Calories", f"{totals['energy_kcal']} kcal")
                
                st.table({
                    "Nutrient": ["Carbs", "Protein", "Fat", "Sugar", "Fiber"],
                    "Amount (g)": [
                        totals["carb_g"],
                        totals["protein_g"],
                        totals["fat_g"],
                        totals["freesugar_g"],
                        totals["fibre_g"]
                    ]
                })

else:  
    json_input = st.text_area("Paste nutrition JSON:", height=200)

    if st.button("Process JSON"):
        try:
            data = json.loads(json_input)
            st.success("✅ Valid JSON format")

            if isinstance(data, list):
                for i, dish_entry in enumerate(data):
                    result = process_dish_entry_streamlit(dish_entry, food_data)

                    with st.expander(f"Dish {i+1}: {result['dish']}"):
                        st.markdown("### 📝 Log")
                        for l in result["log"]:
                            st.write(l)
                        if result["issues"]:
                            st.warning(f"Issues: {result['issues']}")

                        st.markdown("### 🥗 Extracted Ingredients")
                        st.write(result["ingredients"])
                        if result["unmatched"]:
                            st.warning(f"Unmatched ingredients: {result['unmatched']}")
                        st.markdown("### 🍽️ Category & Serving")
                        st.write(f"{result['category']} ({result['serving_weight']}g per serving)")
                        st.markdown("### 📊 Nutrition per Serving")
                        st.json(result["nutrition_per_serving"])
                        st.markdown("### 🔬 Matched Nutrition Details")
                        st.json(result["matched"])
            else:
                st.error("JSON must be a list of dish entries.")

        except json.JSONDecodeError as e:
            st.error(f"❌ Invalid JSON: {str(e)}")
