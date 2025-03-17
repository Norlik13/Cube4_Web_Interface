from django.shortcuts import render, redirect
from django.contrib import messages
from App.models import Customer
from Cube4_Application_web.forms import LoginForm

import requests
from django.shortcuts import render, redirect
from django.contrib import messages
from Cube4_Application_web.forms import LoginForm

API_BASE_URL = "http://localhost:5000"


def login_view(request):
	if request.method == 'POST':
		form = LoginForm(request.POST)
		if form.is_valid():
			customer_name = form.cleaned_data['customer_name']
			password = form.cleaned_data['password']

			# Send authentication request to the API
			response = requests.post(
				f"{API_BASE_URL}/customers/authenticate",
				json={"customer_name": customer_name, "password": password}
			)

			if response.status_code == 200:
				user_data = response.json()
				request.session['customer_id'] = user_data['idCustomer']
				request.session['customer_name'] = user_data['customer_name']
				messages.success(request, "Login successful!")
				return redirect('wine_list')
			else:
				messages.error(request, "Invalid credentials.")

	else:
		form = LoginForm()

	return render(request, 'login.html', {'form': form})


def logout_view(request):
	request.session.flush()
	return redirect('login')

def wine_list_view(request):
	if 'customer_id' not in request.session:
		return redirect('login')

	response = requests.get(f"{API_BASE_URL}/wines/")

	if response.status_code == 200:
		wines = response.json()
	else:
		wines = []  # Fallback if API request fails

	return render(request, 'wines.html', {'wines': wines})


def add_to_cart(request, wine_id):
	if request.method == "POST":
		quantity = int(request.POST.get('quantity', 1))

		if 'cart' not in request.session:
			request.session['cart'] = {}

		cart = request.session['cart']

		if str(wine_id) in cart:
			cart[str(wine_id)]['quantity'] += quantity
		else:
			wine_response = requests.get(f"{API_BASE_URL}/wines/{wine_id}")
			if wine_response.status_code == 200:
				wine = wine_response.json()
				cart[str(wine_id)] = {
					'cuvee_name': wine['cuvee_name'],
					'selling_price': wine['selling_price'],
					'quantity': quantity
				}

		request.session['cart'] = cart
		messages.success(request, f"Added {quantity} to cart!")
		return redirect('wine_list')



def view_cart(request):
	cart = request.session.get('cart', {})
	return render(request, 'cart.html', {'cart': cart})


def remove_from_cart(request, wine_id):
	cart = request.session.get('cart', {})
	if str(wine_id) in cart:
		del cart[str(wine_id)]
		request.session['cart'] = cart
		messages.success(request, "Removed from cart!")

	return redirect('view_cart')


def checkout(request):
	if 'customer_id' not in request.session:
		return redirect('login')

	cart = request.session.get('cart', {})
	if not cart:
		return redirect('view_cart')

	order_data = {
		"customer_idcustomer": request.session['customer_id'],
		"status": "processing",
		"order_details": [
			{"Wine_idWine": int(wine_id), "quantity": item['quantity']}
			for wine_id, item in cart.items()
		]
	}

	response = requests.post(f"{API_BASE_URL}/orders/", json=order_data)

	if response.status_code == 201:
		for wine_id, item in cart.items():
			wine_response = requests.get(f"{API_BASE_URL}/wines/{wine_id}")
			if wine_response.status_code == 200:
				wine = wine_response.json()
				new_stock_quantity = wine['stock_quantity'] - item['quantity']
				if new_stock_quantity < 24:
					bottles_to_order = 48 - new_stock_quantity
					order_data = {
						"provider_idprovider": wine['Provider']['Provider_id'],
						"status": "processing",
						"order_details": [
							{"Wine_idWine": int(wine_id), "quantity": bottles_to_order}
							for wine_id, item in cart.items()
						]
					}
					requests.post(f"{API_BASE_URL}/orders/", json=order_data)
				else:
					requests.put(f"{API_BASE_URL}/wines/inventory/{wine_id}", json={"stock_quantity": new_stock_quantity})
			else:
				messages.error(request, f"Failed to retrieve wine data for wine ID {wine_id}")

		request.session['cart'] = {}
		messages.success(request, "Order placed successfully!")
	else:
		messages.error(request, "Failed to place order.")

	return redirect('view_cart')