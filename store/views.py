import django
from django.contrib.auth.models import User
from store.models import Address, Cart, Category, Order, Product
from django.shortcuts import redirect, render, get_object_or_404
from .forms import RegistrationForm, AddressForm
from django.contrib import messages
from django.views import View
import decimal
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator # for Class Based Views
from django.db.models import Count
from django.http import HttpResponse, JsonResponse
import json, os

from django.contrib.auth import login as auth_login, authenticate
from django.contrib import messages
from django.core.mail import send_mail
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from .forms import LoginForm
from django_ratelimit.decorators import ratelimit

from django.core.management.base import BaseCommand
from django.core.mail import EmailMessage


# Create your views here.

def home(request):
    messages.success(request, '')
    cat_product_count = []
    categories = Category.objects.filter(is_active=True, is_featured=True)[:6]
    for cat in categories:
        count = Product.objects.filter(category=cat, is_active=True).count()
        cat_product_count.append(count)
    products = Product.objects.filter(is_active=True, is_featured=True)[:8]
    just_arrived_products = Product.objects.filter(is_active=True)[:8]
    context = {
        'categories': zip(categories, cat_product_count),
        'products': products,
        'just_arrived_products': just_arrived_products,
        'cat_product_count' : cat_product_count
    }
    return render(request, 'store/home.html', context)

def contact(request):
    return render(request, 'store/contact.html')


def detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    related_products = Product.objects.exclude(id=product.id).filter(is_active=True, category=product.category)
    context = {
        'product': product,
        'related_products': related_products,

    }
    return render(request, 'store/detail.html', context)


def all_categories(request):
    categories = Category.objects.filter(is_active=True)
    return render(request, 'store/categories.html', {'categories':categories})


def category_products(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(is_active=True, category=category)
    categories = Category.objects.filter(is_active=True)
    context = {
        'category': category,
        'products': products,
        'categories': categories,
    }
    return render(request, 'store/category_products.html', context)


# Authentication Starts Here

class RegistrationView(View):
    def get(self, request):
        form = RegistrationForm()
        return render(request, 'account/register.html', {'form': form})
    
    def post(self, request):
        form = RegistrationForm(request.POST)
        if form.is_valid():
            messages.success(request, "Congratulations! Registration Successful!")
            form.save()
        return render(request, 'account/register.html', {'form': form})



@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def custom_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                auth_login(request, user)
                subject = 'Login Notification'
                message = 'You have successfully logged in.'
                sender_email = 'your@example.com'
                recipient_list = [user.email]
                send_mail(subject, message, sender_email, recipient_list)
                messages.success(request, 'Login successful. Check your email for notification.')
                return HttpResponseRedirect(reverse_lazy('store:home'))
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            print("Form is invalid:", form.errors)
            return render(request, 'account/login.html', {'form': form})
    else:
        form = LoginForm()
    
    return render(request, 'account/login.html', {'form': form})



        

@login_required
def profile(request):
    addresses = Address.objects.filter(user=request.user)
    orders = Order.objects.filter(user=request.user)
    return render(request, 'account/profile.html', {'addresses':addresses, 'orders':orders})


@method_decorator(login_required, name='dispatch')
class AddressView(View):
    def get(self, request):
        form = AddressForm()
        return render(request, 'account/add_address.html', {'form': form})

    def post(self, request):
        form = AddressForm(request.POST)
        if form.is_valid():
            user=request.user
            locality = form.cleaned_data['locality']
            city = form.cleaned_data['city']
            state = form.cleaned_data['state']
            reg = Address(user=user, locality=locality, city=city, state=state)
            reg.save()
            messages.success(request, "New Address Added Successfully.")
        return redirect('store:profile')


@login_required
def remove_address(request, id):
    a = get_object_or_404(Address, user=request.user, id=id)
    a.delete()
    messages.success(request, "Address removed.")
    return redirect('store:profile')

@login_required
def add_to_cart(request):
    data = json.loads(request.body)
    product_id = data['prod_id']  
    user = request.user
    product = get_object_or_404(Product, id=product_id)
    item_already_in_cart = Cart.objects.filter(product=product_id, user=user)
    increment = 0
    if item_already_in_cart:
        cp = get_object_or_404(Cart, product=product_id, user=user)
        cp.quantity += 1
        cp.save()
    else:
        Cart(user=user, product=product).save()
        increment += 1
    return JsonResponse({'msg':"Success", 'increment':increment}, status=201)



@login_required
def cart(request):
    user = request.user
    cart_products = Cart.objects.filter(user=user)

    # Display Total on Cart Page
    amount = decimal.Decimal(0)
    shipping_amount = decimal.Decimal(10)
    # using list comprehension to calculate total amount based on quantity and shipping
    cp = [p for p in Cart.objects.all() if p.user==user]
    if cp:
        for p in cp:
            temp_amount = (p.quantity * p.product.price)
            amount += temp_amount

    # Customer Addresses
    addresses = Address.objects.filter(user=user)

    context = {
        'cart_products': cart_products,
        'amount': amount,
        'shipping_amount': shipping_amount,
        'total_amount': amount + shipping_amount,
        'addresses': addresses,
    }
    return render(request, 'store/cart.html', context)


@login_required
def remove_cart(request):
    data = json.loads(request.body)
    cart_id = data['cart_id']
    if request.method == 'POST':
        c = get_object_or_404(Cart, id=cart_id)
        c.delete()
    return JsonResponse({'msg':"Product removed from cart"}, status=201)


@login_required
def plus_cart(request, cart_id):
    if request.method == 'GET':
        cp = get_object_or_404(Cart, id=cart_id)
        cp.quantity += 1
        cp.save()
    return redirect('store:cart')


@login_required
def minus_cart(request, cart_id):
    if request.method == 'GET':
        cp = get_object_or_404(Cart, id=cart_id)
        # Remove the Product if the quantity is already 1
        if cp.quantity == 1:
            cp.delete()
        else:
            cp.quantity -= 1
            cp.save()
    return redirect('store:cart')


@login_required
def checkout(request):
    user = request.user
    cart_products = Cart.objects.filter(user=user)
    if not cart_products.exists():
        return redirect('store:home')
    # Display Total on Cart Page
    amount = decimal.Decimal(0)
    shipping_amount = decimal.Decimal(10)
    # using list comprehension to calculate total amount based on quantity and shipping
    cp = [p for p in Cart.objects.all() if p.user==user]
    if cp:
        for p in cp:
            temp_amount = (p.quantity * p.product.price)
            amount += temp_amount

    # Customer Addresses
    addresses = Address.objects.filter(user=user)

    context = {
        'cart_products': cart_products,
        'amount': amount,
        'shipping_amount': shipping_amount,
        'total_amount': amount + shipping_amount,
        'addresses': addresses,
    }
    return render(request, 'store/checkout.html', context)

@login_required
def placeOrder(request):
    user = request.user
    address_id = request.GET.get('address')
    address = get_object_or_404(Address, id=address_id)
    # Get all the products of User in Cart
    cart = Cart.objects.filter(user=user)
    for c in cart:
        # Saving all the products from Cart to Order
        Order(user=user, address=address, product=c.product, quantity=c.quantity).save()
        # And Deleting from Cart
        c.delete()
    return redirect('store:orders')

@login_required
def orders(request):
    all_orders = Order.objects.filter(user=request.user).order_by('-ordered_date')
    return render(request, 'store/orders.html', {'orders': all_orders})





def shop(request):
    return render(request, 'store/shop.html')





def test(request):
    return render(request, 'store/test.html')


@login_required
def data_backup(request):
    if request.user.is_superuser:
        database_file = 'db.sqlite3'
        if os.path.exists(database_file):
            email = EmailMessage(
                subject='Database Backup',
                body='Attached is the backup of the database.',
                to=[request.user.email],
            )
            email.attach_file(database_file)
            email.send()   
            print("Backup sent")
        else:
            print('Database not found')  
        return redirect('store:home')   
    else:
        return redirect('store:home')