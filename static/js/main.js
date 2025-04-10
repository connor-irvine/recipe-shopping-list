document.addEventListener('DOMContentLoaded', function() {
    // Load recipes when the page loads
    loadRecipes();
    loadStores();

    // Add event listeners
    document.getElementById('add-ingredient').addEventListener('click', addIngredientField);
    document.getElementById('recipe-form').addEventListener('submit', handleRecipeSubmit);
    document.getElementById('recipe-list').addEventListener('click', handleRecipeSelection);
    document.getElementById('search-form').addEventListener('submit', handleSearch);
    document.getElementById('find-stores').addEventListener('click', findNearestStores);
});

// Load recipes from the server
async function loadRecipes() {
    try {
        const response = await fetch('/api/recipes');
        const recipes = await response.json();
        displayRecipes(recipes);
    } catch (error) {
        console.error('Error loading recipes:', error);
    }
}

// Load stores from the server
async function loadStores() {
    try {
        const response = await fetch('/api/stores');
        const stores = await response.json();
        // Store the stores data for later use
        window.stores = stores;
    } catch (error) {
        console.error('Error loading stores:', error);
    }
}

// Display recipes in the recipe list
function displayRecipes(recipes) {
    const recipeList = document.getElementById('recipe-list');
    recipeList.innerHTML = recipes.map(recipe => `
        <div class="list-group-item" data-recipe-id="${recipe.id}">
            <div class="d-flex justify-content-between align-items-center">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" value="${recipe.id}">
                    <label class="form-check-label">${recipe.name}</label>
                </div>
                <button class="btn btn-outline-danger btn-sm delete-recipe" data-recipe-id="${recipe.id}">
                    <i class="bi bi-trash"></i> Delete
                </button>
            </div>
        </div>
    `).join('');

    // Add event listeners for delete buttons
    document.querySelectorAll('.delete-recipe').forEach(button => {
        button.addEventListener('click', handleDeleteRecipe);
    });
}

// Add new ingredient field to the form
function addIngredientField() {
    const ingredientsList = document.getElementById('ingredients-list');
    const newIngredient = document.createElement('div');
    newIngredient.className = 'input-group mb-2';
    newIngredient.innerHTML = `
        <input type="text" class="form-control ingredient-name" placeholder="Ingredient name">
        <input type="number" class="form-control ingredient-amount" placeholder="Amount">
        <button type="button" class="btn btn-outline-danger remove-ingredient">×</button>
    `;
    ingredientsList.appendChild(newIngredient);
}

// Handle recipe form submission
async function handleRecipeSubmit(event) {
    event.preventDefault();
    
    const name = document.getElementById('recipe-name').value;
    const instructions = document.getElementById('instructions').value;
    
    // Gather ingredients
    const ingredients = {};
    document.querySelectorAll('.ingredient-row').forEach(row => {
        const name = row.querySelector('.ingredient-name').value;
        const amount = parseFloat(row.querySelector('.ingredient-amount').value);
        if (name && amount) {
            ingredients[name] = amount;
        }
    });

    try {
        const response = await fetch('/api/recipes', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name,
                ingredients,
                instructions
            })
        });

        if (response.ok) {
            // Clear form and reload recipes
            event.target.reset();
            loadRecipes();
        }
    } catch (error) {
        console.error('Error adding recipe:', error);
    }
}

// Handle recipe selection
function handleRecipeSelection(event) {
    const checkbox = event.target.closest('input[type="checkbox"]');
    if (checkbox) {
        updateShoppingList();
    }
}

// Update shopping list based on selected recipes
async function updateShoppingList() {
    const selectedRecipes = Array.from(document.querySelectorAll('input[type="checkbox"]:checked'))
        .map(checkbox => checkbox.value);

    const shoppingList = document.getElementById('shopping-list');
    const storeComparison = document.getElementById('store-comparison');

    if (selectedRecipes.length === 0) {
        shoppingList.innerHTML = '<p>Select recipes to generate shopping list</p>';
        storeComparison.innerHTML = '';
        return;
    }

    try {
        const response = await fetch('/api/calculate-shopping-list', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                recipe_ids: selectedRecipes
            })
        });

        const data = await response.json();
        
        // Display shopping list
        shoppingList.innerHTML = `
            <h6>Ingredients:</h6>
            <ul class="list-group">
                ${Object.entries(data.shopping_list).map(([ingredient, amount]) => `
                    <li class="list-group-item d-flex justify-content-between align-items-center">
                        ${ingredient}
                        <span class="badge bg-primary rounded-pill">${amount}</span>
                    </li>
                `).join('')}
            </ul>
        `;

        // Display store comparison
        storeComparison.innerHTML = `
            <h6>Store Comparison:</h6>
            <div class="list-group">
                ${Object.entries(data.store_costs).map(([store, cost]) => `
                    <div class="list-group-item ${store === data.cheapest_store ? 'list-group-item-success' : ''}">
                        <div class="d-flex justify-content-between align-items-center">
                            <strong>${store}</strong>
                            <span class="badge bg-primary rounded-pill">$${cost.toFixed(2)}</span>
                        </div>
                    </div>
                `).join('')}
            </div>
            <div class="alert alert-success mt-3">
                <strong>Best deal:</strong> ${data.cheapest_store} - Total: $${data.total_cost.toFixed(2)}
            </div>
        `;
    } catch (error) {
        console.error('Error calculating shopping list:', error);
        shoppingList.innerHTML = '<div class="alert alert-danger">Failed to generate shopping list. Please try again.</div>';
    }
}

// Handle recipe search
async function handleSearch(event) {
    event.preventDefault();
    const query = document.getElementById('search-query').value;
    const searchResults = document.getElementById('search-results');
    
    // Show loading state
    searchResults.innerHTML = '<div class="text-center"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>';
    
    try {
        const response = await fetch('/api/search-recipes', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query })
        });

        const data = await response.json();
        
        if (response.ok) {
            // Display search results
            searchResults.innerHTML = `
                <h6 class="mb-3">Found ${data.recipes.length} recipes:</h6>
                <div class="list-group">
                    ${data.recipes.map(recipe => `
                        <div class="list-group-item">
                            <h6 class="mb-1">${recipe.name}</h6>
                            <p class="mb-1"><strong>Ingredients:</strong></p>
                            <ul class="mb-1">
                                ${Object.entries(recipe.ingredients).map(([ingredient, amount]) => `
                                    <li>${ingredient}: ${amount}</li>
                                `).join('')}
                            </ul>
                            <p class="mb-1"><strong>Instructions:</strong></p>
                            <p class="mb-0">${recipe.instructions}</p>
                        </div>
                    `).join('')}
                </div>
            `;
            
            // Refresh the recipe list to include new recipes
            loadRecipes();
        } else {
            searchResults.innerHTML = `<div class="alert alert-danger">${data.error || 'Failed to search recipes'}</div>`;
        }
    } catch (error) {
        console.error('Error searching recipes:', error);
        searchResults.innerHTML = '<div class="alert alert-danger">Failed to search recipes. Please try again.</div>';
    }
}

// Handle recipe deletion
async function handleDeleteRecipe(event) {
    event.preventDefault();
    event.stopPropagation();
    
    const recipeId = event.currentTarget.dataset.recipeId;
    if (!confirm('Are you sure you want to delete this recipe?')) {
        return;
    }

    try {
        const response = await fetch(`/api/recipes/${recipeId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            // Remove the recipe from the list
            const recipeElement = document.querySelector(`[data-recipe-id="${recipeId}"]`);
            if (recipeElement) {
                recipeElement.remove();
            }
            // Update shopping list if needed
            updateShoppingList();
        } else {
            const data = await response.json();
            alert(data.error || 'Failed to delete recipe');
        }
    } catch (error) {
        console.error('Error deleting recipe:', error);
        alert('Failed to delete recipe. Please try again.');
    }
}

// Format price in GBP
function formatPrice(price) {
    return new Intl.NumberFormat('en-GB', {
        style: 'currency',
        currency: 'GBP'
    }).format(price);
}

// Find nearest stores
async function findNearestStores() {
    const postcode = document.getElementById('postcode').value;
    if (!postcode) {
        alert('Please enter a postcode');
        return;
    }

    try {
        const response = await fetch('/api/find-nearest-stores', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ postcode })
        });
        const data = await response.json();
        
        if (data.error) {
            alert(data.error);
            return;
        }

        const storesList = document.getElementById('stores-list');
        storesList.innerHTML = data.stores.map(store => `
            <div class="store-item">
                <h3>${store.name}</h3>
                <p>${store.address}</p>
                <p>Postcode: ${store.postcode}</p>
                <p>Distance: ${store.distance} km</p>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to find nearest shops');
    }
}

// Calculate shopping list
async function calculateShoppingList() {
    const selectedRecipes = Array.from(document.querySelectorAll('input[name="recipe"]:checked'))
        .map(checkbox => parseInt(checkbox.value));

    if (selectedRecipes.length === 0) {
        alert('Please select at least one recipe');
        return;
    }

    try {
        const response = await fetch('/api/calculate-shopping-list', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ recipe_ids: selectedRecipes })
        });
        const data = await response.json();
        
        if (data.error) {
            alert(data.error);
            return;
        }

        const shoppingList = document.getElementById('shopping-list');
        shoppingList.innerHTML = `
            <h3>Shopping List</h3>
            <div class="ingredients">
                ${Object.entries(data.shopping_list).map(([ingredient, amount]) => `
                    <div class="ingredient">
                        <span>${ingredient}:</span>
                        <span>${amount}</span>
                    </div>
                `).join('')}
            </div>
            <h3>Prices by Shop</h3>
            ${Object.entries(data.store_costs).map(([store, costs]) => `
                <div class="store-costs">
                    <h4>${store}</h4>
                    <div class="items">
                        ${Object.entries(costs.items).map(([item, price]) => `
                            <div class="item">
                                <span>${item}:</span>
                                <span>${formatPrice(price)}</span>
                            </div>
                        `).join('')}
                    </div>
                    <div class="total">
                        <strong>Total: ${formatPrice(costs.total)}</strong>
                    </div>
                </div>
            `).join('')}
            <div class="cheapest-store">
                <h3>Best Value</h3>
                <p>${data.cheapest_store} - ${formatPrice(data.total_cost)}</p>
            </div>
        `;
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to generate shopping list');
    }
} 