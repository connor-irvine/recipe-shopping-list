from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import json
import os
from datetime import datetime
from openai import OpenAI
import requests
from math import radians, sin, cos, sqrt, asin
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///recipes.db'
db = SQLAlchemy(app)

# Initialize OpenAI client with API key from environment variable
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    ingredients = db.Column(db.JSON, nullable=False)
    instructions = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Store(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    prices = db.Column(db.JSON, nullable=False)
    address = db.Column(db.String(200), nullable=False)
    zip_code = db.Column(db.String(20), nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the distance between two points on earth using Haversine formula"""
    R = 6371  # Earth's radius in kilometers

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/recipes', methods=['GET'])
def get_recipes():
    recipes = Recipe.query.all()
    return jsonify([{
        'id': recipe.id,
        'name': recipe.name,
        'ingredients': recipe.ingredients,
        'instructions': recipe.instructions
    } for recipe in recipes])

@app.route('/api/recipes', methods=['POST'])
def add_recipe():
    data = request.json
    new_recipe = Recipe(
        name=data['name'],
        ingredients=data['ingredients'],
        instructions=data['instructions']
    )
    db.session.add(new_recipe)
    db.session.commit()
    return jsonify({'message': 'Recipe added successfully'})

@app.route('/api/stores', methods=['GET'])
def get_stores():
    stores = Store.query.all()
    return jsonify([{
        'id': store.id,
        'name': store.name,
        'prices': store.prices
    } for store in stores])

@app.route('/api/calculate-shopping-list', methods=['POST'])
def calculate_shopping_list():
    try:
        recipe_ids = request.json.get('recipe_ids', [])
        if not recipe_ids:
            return jsonify({'error': 'No recipes selected'}), 400

        recipes = Recipe.query.filter(Recipe.id.in_(recipe_ids)).all()
        if not recipes:
            return jsonify({'error': 'No recipes found'}), 404

        stores = Store.query.all()
        if not stores:
            return jsonify({'error': 'No stores found'}), 404
        
        # Normalize and combine ingredients from selected recipes
        shopping_list = {}
        for recipe in recipes:
            for ingredient, amount in recipe.ingredients.items():
                # Normalize ingredient name (remove quantities from name)
                normalized_name = ingredient.split('(')[0].strip().lower()
                if normalized_name in shopping_list:
                    shopping_list[normalized_name] = f"{shopping_list[normalized_name]}, plus {amount}"
                else:
                    shopping_list[normalized_name] = amount

        # Get price estimates for each store
        store_costs = {}
        for store in stores:
            store_total = 0
            store_items = {}
            
            # Calculate costs based on store's price list
            for ingredient in shopping_list.keys():
                base_price = 0
                # Try to find matching ingredient in store prices
                for store_ingredient, price in store.prices.items():
                    if ingredient in store_ingredient.lower():
                        base_price = price
                        break
                
                store_items[ingredient] = base_price
                store_total += base_price

            store_costs[store.name] = {
                'items': store_items,
                'total': store_total
            }

        # Find cheapest store
        cheapest_store = min(store_costs.items(), key=lambda x: x[1]['total'])
        
        return jsonify({
            'shopping_list': shopping_list,
            'store_costs': store_costs,
            'cheapest_store': cheapest_store[0],
            'total_cost': cheapest_store[1]['total']
        })

    except Exception as e:
        print(f"Error in calculate_shopping_list: {str(e)}")
        return jsonify({'error': 'Failed to generate shopping list'}), 500

@app.route('/api/generate-recipe', methods=['POST'])
def generate_recipe():
    recipe_name = request.json.get('name')
    if not recipe_name:
        return jsonify({'error': 'Recipe name is required'}), 400

    try:
        # Generate recipe using OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful chef assistant. Generate a recipe with ingredients and instructions in JSON format."},
                {"role": "user", "content": f"Generate a recipe for {recipe_name}. Return the response in this exact JSON format: {{\"ingredients\": {{\"ingredient1\": amount, \"ingredient2\": amount}}, \"instructions\": \"step by step instructions\"}}"}
            ]
        )
        
        # Parse the response
        recipe_data = json.loads(response.choices[0].message.content)
        
        # Create new recipe
        new_recipe = Recipe(
            name=recipe_name,
            ingredients=recipe_data['ingredients'],
            instructions=recipe_data['instructions']
        )
        db.session.add(new_recipe)
        db.session.commit()
        
        return jsonify({
            'message': 'Recipe generated successfully',
            'recipe': {
                'id': new_recipe.id,
                'name': new_recipe.name,
                'ingredients': new_recipe.ingredients,
                'instructions': new_recipe.instructions
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search-recipes', methods=['POST'])
def search_recipes():
    query = request.json.get('query')
    if not query:
        return jsonify({'error': 'Search query is required'}), 400

    try:
        # Use OpenAI to search for recipes based on the query
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful chef assistant. Generate 3 recipe suggestions based on the user's search query. Each recipe should include a name, ingredients with amounts, and step-by-step instructions."},
                {"role": "user", "content": f"Find recipes related to: {query}. Return exactly 3 recipes in this JSON format: {{\"recipes\": [{{\"name\": \"Recipe Name\", \"ingredients\": {{\"ingredient1\": \"amount1\", \"ingredient2\": \"amount2\"}}, \"instructions\": \"step by step instructions\"}}]}}"}
            ]
        )
        
        # Parse the response
        recipe_data = json.loads(response.choices[0].message.content)
        
        # Save all recipes to database
        saved_recipes = []
        for recipe in recipe_data['recipes']:
            new_recipe = Recipe(
                name=recipe['name'],
                ingredients=recipe['ingredients'],
                instructions=recipe['instructions']
            )
            db.session.add(new_recipe)
            db.session.commit()
            
            saved_recipes.append({
                'id': new_recipe.id,
                'name': new_recipe.name,
                'ingredients': new_recipe.ingredients,
                'instructions': new_recipe.instructions
            })
        
        return jsonify({
            'message': 'Recipes found successfully',
            'recipes': saved_recipes
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recipes/<int:recipe_id>', methods=['DELETE'])
def delete_recipe(recipe_id):
    try:
        recipe = Recipe.query.get_or_404(recipe_id)
        db.session.delete(recipe)
        db.session.commit()
        return jsonify({'message': 'Recipe deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/find-nearest-stores', methods=['POST'])
def find_nearest_stores():
    postcode = request.json.get('postcode')
    if not postcode:
        return jsonify({'error': 'Postcode is required'}), 400

    try:
        # Get coordinates for the provided postcode using postcodes.io
        response = requests.get(
            f'https://api.postcodes.io/postcodes/{postcode}'
        )
        location_data = response.json()

        if not location_data.get('result'):
            return jsonify({'error': 'Could not find location for the provided postcode'}), 400

        user_lat = float(location_data['result']['latitude'])
        user_lon = float(location_data['result']['longitude'])

        # Get all stores and calculate distances
        stores = Store.query.all()
        stores_with_distance = []
        
        for store in stores:
            if store.latitude and store.longitude:
                distance = haversine_distance(user_lat, user_lon, store.latitude, store.longitude)
                stores_with_distance.append({
                    'id': store.id,
                    'name': store.name,
                    'address': store.address,
                    'postcode': store.zip_code,
                    'distance': round(distance, 2),
                    'prices': store.prices
                })

        # Sort stores by distance
        stores_with_distance.sort(key=lambda x: x['distance'])

        return jsonify({
            'stores': stores_with_distance
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/initialize-stores', methods=['POST'])
def initialize_stores():
    try:
        # Clear existing stores
        Store.query.delete()
        
        # Add UK stores with sample locations
        stores = [
            # North East Stores
            Store(
                name="Tesco Extra Whitley Bay",
                address="Newsteads Drive, Whitley Bay",
                zip_code="NE25 9UZ",
                latitude=55.0478,
                longitude=-1.4827,
                prices={
                    "all-purpose flour": 1.65,
                    "baking soda": 0.80,
                    "brown sugar": 1.20,
                    "eggs": 2.40,
                    "granulated sugar": 1.10,
                    "salt": 0.60,
                    "chocolate chips": 2.15,
                    "unsalted butter": 2.65,
                    "vanilla extract": 1.40
                }
            ),
            Store(
                name="Sainsbury's Whitley Bay",
                address="Newsteads Drive, Whitley Bay",
                zip_code="NE25 9UT",
                latitude=55.0475,
                longitude=-1.4830,
                prices={
                    "all-purpose flour": 1.75,
                    "baking soda": 0.85,
                    "brown sugar": 1.30,
                    "eggs": 2.60,
                    "granulated sugar": 1.20,
                    "salt": 0.65,
                    "chocolate chips": 2.25,
                    "unsalted butter": 2.75,
                    "vanilla extract": 1.60
                }
            ),
            Store(
                name="Morrisons Whitley Bay",
                address="Hillheads Road, Whitley Bay",
                zip_code="NE25 9UX",
                latitude=55.0461,
                longitude=-1.4789,
                prices={
                    "all-purpose flour": 1.60,
                    "baking soda": 0.75,
                    "brown sugar": 1.15,
                    "eggs": 2.35,
                    "granulated sugar": 1.05,
                    "salt": 0.55,
                    "chocolate chips": 2.10,
                    "unsalted butter": 2.60,
                    "vanilla extract": 1.30
                }
            ),
            Store(
                name="Tesco Metro Newcastle",
                address="Clayton Street, Newcastle upon Tyne",
                zip_code="NE1 5PB",
                latitude=54.9697,
                longitude=-1.6157,
                prices={
                    "all-purpose flour": 1.70,
                    "baking soda": 0.82,
                    "brown sugar": 1.22,
                    "eggs": 2.45,
                    "granulated sugar": 1.12,
                    "salt": 0.62,
                    "chocolate chips": 2.20,
                    "unsalted butter": 2.70,
                    "vanilla extract": 1.45
                }
            ),
            Store(
                name="Sainsbury's Newcastle",
                address="John Dobson Street, Newcastle upon Tyne",
                zip_code="NE1 8HL",
                latitude=54.9741,
                longitude=-1.6120,
                prices={
                    "all-purpose flour": 1.80,
                    "baking soda": 0.87,
                    "brown sugar": 1.32,
                    "eggs": 2.65,
                    "granulated sugar": 1.22,
                    "salt": 0.67,
                    "chocolate chips": 2.30,
                    "unsalted butter": 2.80,
                    "vanilla extract": 1.65
                }
            ),
            # Keep one London store for comparison
            Store(
                name="Waitrose London",
                address="200 Oxford Street, London",
                zip_code="W1D 1NU",
                latitude=51.5152,
                longitude=-0.1449,
                prices={
                    "all-purpose flour": 2.25,
                    "baking soda": 1.15,
                    "brown sugar": 1.65,
                    "eggs": 3.25,
                    "granulated sugar": 1.55,
                    "salt": 0.85,
                    "chocolate chips": 2.85,
                    "unsalted butter": 3.25,
                    "vanilla extract": 2.25
                }
            )
        ]
        
        for store in stores:
            db.session.add(store)
        
        db.session.commit()
        return jsonify({'message': 'Stores initialized successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=8000) 