# Recipe Shopping List App

A web application that helps you create shopping lists for dinner recipes and compares prices across different stores to find the best deals.

## Features

- Add and manage recipes with ingredients and instructions
- Create shopping lists from multiple recipes
- Compare prices across different stores
- Automatically find the cheapest store for your shopping list
- Modern and responsive user interface

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd recipe-shopping-list
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

4. Initialize the database:
```bash
python
>>> from app import db
>>> db.create_all()
>>> exit()
```

5. Run the application:
```bash
python app.py
```

6. Open your web browser and navigate to `http://localhost:5000`

## Usage

1. Add Recipes:
   - Click on "Add New Recipe"
   - Enter the recipe name
   - Add ingredients with their amounts
   - Add cooking instructions
   - Click "Add Recipe" to save

2. Create Shopping List:
   - Select one or more recipes from the list
   - The shopping list will automatically update
   - View the store comparison to find the best deals

3. View Store Comparison:
   - See prices for each store
   - The cheapest store will be highlighted
   - Total cost is displayed for each store

## Adding Store Prices

To add or update store prices, you can use the Python shell:

```python
from app import db, Store

# Add a new store
new_store = Store(
    name='Store Name',
    prices={
        'ingredient1': 1.99,
        'ingredient2': 2.49,
        # Add more ingredients and prices
    }
)
db.session.add(new_store)
db.session.commit()
```

## Contributing

Feel free to submit issues and enhancement requests! 