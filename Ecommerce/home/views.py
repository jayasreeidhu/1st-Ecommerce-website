from django.http import HttpResponse
import random
from django.shortcuts import render, redirect,get_object_or_404
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout,login as auth_login
from django.contrib.auth.decorators import login_required
import datetime
from django.template.loader import render_to_string
import pdfkit
import os
from django.utils.timezone import now
from django.core.cache import cache
from products.models import Product,ProductVariant,Order,Cart,CartItem,ProductOffer, CategoryOffer, ReferralOffer,OrderItem
from django.contrib.auth import update_session_auth_hash
from .models import Profile
from .forms import UserUpdateForm, ProfileUpdateForm
from django.views.decorators.cache import never_cache
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from .models import Address
from .forms import AddressForm
import json
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.forms import SetPasswordForm
from .forms import CustomPasswordResetForm
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.contrib.auth import get_user_model
from .models import Wallet, Transaction
import razorpay
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
import paypalrestsdk
from django.urls import reverse
from django.db import transaction
import logging
from django.contrib.auth import get_backends
from razorpay.errors import BadRequestError, ServerError
import uuid

logger = logging.getLogger(__name__)
  # Adjust the import according to your project structure


# client = razorpay.Client(auth=("", ""))


client = razorpay.Client(auth=("", ""))




paypalrestsdk.configure({
    "mode": "sandbox",  # Change to "live" for production
    "client_id": "",
    "client_secret": "",
})




# Create your views here.
def index(request):
    return render(request,'user/index.html')


@login_required
def google_login_redirect(request):
    return redirect(request,'user/index.html')







# def user_login(request):
#     if request.method == 'POST':
#         username = request.POST['username']
#         password = request.POST['password']

#         user=authenticate(username=username,password=password)

#         if user is not None:
#             auth_login(request,user)
#             return render(request,"user/index.html")

#         else:
#             messages.error(request, 'Invalid username or password. Please try again.')
#             return redirect('login')
#     return render(request,'user/login.html')

# def user_login(request):
#     if request.method == 'POST':
#         email = request.POST['email']
#         password = request.POST['password']

#         user = authenticate(request, username=email, password=password)

#         if user is not None:
#             auth_login(request, user)
#             return render(request, "user/index.html")

#         else:
#             messages.error(request, 'Invalid email address or password. Please try again.')
#             return redirect('login')
#     return render(request, 'user/login.html')
logger = logging.getLogger(__name__)

User = get_user_model()

def user_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Log email and password for debugging (Do not use in production)
        logger.debug(f"Email: {email}, Password: {password}")

        try:
            users = User.objects.filter(email=email)
            if users.exists():
                user = None
                for user_obj in users:
                    user = authenticate(username=user_obj.username, password=password)
                    if user is not None:
                        break
            else:
                user = None
        except User.DoesNotExist:
            user = None

        if user is not None:
            auth_login(request, user)
            return render(request, "user/index.html")
        else:
            messages.error(request, 'Invalid email address or password. Please try again.')
            return redirect('login')
    return render(request, 'user/login.html')
  
def signup(request):
    if request.method == "POST":
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        
        myuser = User.objects.create_user(username, email, password)
        myuser.save()

        otp = random.randint(1000, 9999)
        expiry_time = now() + datetime.timedelta(minutes=5)  # OTP expires in 5 minutes

        # Store OTP and expiry in the session or cache
        cache.set(email, {'otp': otp, 'expiry': expiry_time}, timeout=300)

        send_mail(
            'Your OTP for Verification',
            f'Your OTP is: {otp}. It will expire in 5 minutes.',
            'jayasreeidhunov@gmail.com',  # Replace email
            [email],
            fail_silently=False,
        )

        request.session['email'] = email
        messages.success(request, "OTP sent to your email. Please verify.")
        return redirect('otp_verification')

    return render(request, 'user/signup.html')


def otp_verification(request):
    if request.method == "POST":
        entered_otp = request.POST.get('otp')
        email = request.session.get('email')

        otp_data = cache.get(email)
        if not otp_data:
            messages.error(request, "OTP expired. Please request a new one.")
            return redirect('signup')  # Redirect to signup or OTP resend

        stored_otp = otp_data['otp']
        expiry = otp_data['expiry']

        if now() > expiry:
            messages.error(request, "OTP expired. Please request a new one.")
            return redirect('signup')

        if str(entered_otp) == str(stored_otp):
            cache.delete(email)  # Clear OTP from cache
            messages.success(request, "OTP verified successfully!")
            return redirect('login')
        else:
            messages.error(request, "Invalid OTP. Please try again.")

    return render(request, 'user/otp_verification.html')


def resend_otp(request):
    email = request.session.get('email')
    if not email:
        messages.error(request, "Session expired. Please sign up again.")
        return redirect('signup')

    otp = random.randint(1000, 9999)
    expiry_time = now() + datetime.timedelta(minutes=5)

    cache.set(email, {'otp': otp, 'expiry': expiry_time}, timeout=300)

    send_mail(
        'Your New OTP for Verification',
        f'Your new OTP is: {otp}. It will expire in 5 minutes.',
        'jayasreeidhunov@gmail.com',  
        [email],
        fail_silently=False,
    )

    messages.success(request, "A new OTP has been sent to your email.")
    return redirect('otp_verification')


@login_required
def logout_view(request):
    logout(request)
    return redirect('index')

@login_required
@never_cache
def profile(request):
    if request.user.is_superuser:
        return redirect("index") 
    if request.method == "POST":
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, instance=request.user.profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("user_profile")  # Ensure this is the correct URL name
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)

    return render(request, "user/user_profile.html", {
        "user_form": user_form,
        "profile_form": profile_form,
    })
    
    # response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    # return response

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important to keep the user logged in
            messages.success(request, 'Your password was successfully updated!')
            return redirect('index')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'user/change_password.html', {
        'form': form
    })



@login_required
def add_address(request):
    next_url = request.GET.get('next', 'checkoutpage')  # Default to checkout page if no address exists

    if request.method == 'POST':	
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            return redirect(next_url)  # Redirect to checkout page if specified
    else:
        form = AddressForm()

    return render(request, 'user/add_Address.html', {'form': form})






@login_required
def edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            return redirect('user_profile')
    else:
        form = AddressForm(instance=address)
    return render(request, 'user/edit_address.html', {'form': form})



@login_required
def delete_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    address.delete()

    # Redirect back to the checkout page if the user came from there
    next_url = request.GET.get('next', 'user_profile')
    return redirect(next_url)



def cart(request):
    return render(request,'user/cart_detail.html')





logger = logging.getLogger(__name__)

@login_required
def checkout(request):
    addresses = Address.objects.filter(user=request.user)
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = CartItem.objects.filter(cart=cart)

    cart_items_with_total = []
    total_price = 0
    discount_amount =  cart.discount_amount if cart.discount_amount else 0

    for item in cart_items:
        item_total = item.product.price * item.quantity
        total_price += item_total
        cart_items_with_total.append({'item': item, 'item_total': item_total})

    # Apply active product offers
    for item in cart_items:
        product_offers = ProductOffer.objects.filter(
            product=item.product,
            start_date__lte=now(),
            end_date__gte=now()
        )
        for offer in product_offers:
            discount_amount += offer.discount_amount * item.quantity

    # Apply active category offers
    for item in cart_items:
        category_offers = CategoryOffer.objects.filter(
            category=item.product.category,
            start_date__lte=now(),
            end_date__gte=now()
        )
        for offer in category_offers:
            discount_amount += (item.product.price * offer.discount_percentage / 100) * item.quantity

    applied_coupon = request.session.get('applied_coupon', None)
    if applied_coupon:
        discount_amount += applied_coupon['discount_amount']

    discount_amount = min(discount_amount, total_price)

    final_price = total_price - discount_amount
    delivery_charge = 60
    final_price += delivery_charge
    final_price = int(final_price) 


    

    if request.method == 'POST':
        selected_address_id = request.POST.get('address_id')
        if not selected_address_id:
            messages.error(request, "Please select an address.")
            return redirect('checkoutpage')

        payment_option = request.POST.get('payment_option')
        if not payment_option:
            messages.error(request, "Please select a payment option.")
            return redirect('checkoutpage')

        selected_address = get_object_or_404(Address, id=selected_address_id, user=request.user)

        # Create Order and OrderItems
        order = Order(
            user=request.user,
            address=selected_address,
            total_price=final_price,
            status='Pending',
            payment_method=payment_option.upper(),
        )
        order.save()

        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )

        logger.info(f"Created order {order.id} with {cart_items.count()} items")

        if payment_option == 'razorpay':
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            payment = client.order.create({
                "amount": final_price * 100,  # Razorpay expects the amount in paise
                "currency": "INR",
                "payment_capture": 1
            })

            order.razorpay_payment_id = payment['id']
            order.save()

            context = {
                'payment': payment,
                'order': order,
                'addresses': addresses,
                'cart_items': cart_items_with_total,
                'total_price': total_price,
                'discount_amount': discount_amount,
                'delivery_charge': delivery_charge,
                'final_price': final_price,
            }
            return render(request, 'user/razorpay_payment.html', context)

        elif payment_option == 'cod':
            order.status = 'Pending'
            order.payment_status = 'Pending'
            order.save()
            order.reduce_stock()  # Reduce stock for COD
            CartItem.objects.filter(cart=cart).delete()  # Clear cart
            messages.success(request, "Order placed successfully with Cash on Delivery!")
            return redirect('my_orders')

    context = {
        'addresses': addresses,
        'cart_items': cart_items_with_total,
        'total_price': total_price,
        'discount_amount': discount_amount,
        'delivery_charge': delivery_charge,
        'final_price': final_price,
    }
    return render(request, 'user/checkoutpage.html', context)




def create_payment(request):
    return render(request, 'payment/create_payment.html') 

@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'user/order_confirmation.html', {'order': order}) 

@login_required
def place_order(request):
    if request.method == 'POST':
        address_id = request.POST.get('address_id')
        payment_option = request.POST.get('payment_option')

        if not address_id:
            messages.error(request, "Please select an address before placing the order.")
            return redirect('checkoutpage')

        if not payment_option:
            messages.error(request, "Please select a payment option.")
            return redirect('checkoutpage')

        selected_address = get_object_or_404(Address, id=address_id, user=request.user)
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items = CartItem.objects.filter(cart=cart)
        total_price = sum(item.product.price * item.quantity for item in cart_items)

        if total_price == 0:
            messages.error(request, "Your cart is empty. Add items before placing the order.")
            return redirect('checkoutpage')

        order = Order.objects.create(
            user=request.user,
            address=selected_address,
            total_price=total_price,
            payment_method=payment_option
        )

        for item in cart_items:
            OrderItem.objects.create(order=order, product=item.product, quantity=item.quantity, price=item.product.price)


        product = item.product
        if product.stock >= item.quantity:
                product.stock -= item.quantity
                product.save()
        else:
                messages.error(request, f"Not enough stock for {product.name}.")
                return redirect('checkoutpage')

        order.save()
        cart_items.delete()


        if payment_option == "cash_on_delivery":
            order.cod_transaction_id = "COD-" + uuid.uuid4().hex[:10]  # Generates a unique ID
            order.save()

        # **Handle PayPal Payment**
        if payment_option == 'PAYPAL':
            request.session['order_id'] = order.id  # Store order ID in session for later reference
            return redirect('paypal_payment', order_id=order.id)  # Redirect to PayPal payment page

        # **Handle Razorpay Payment**
        if payment_option == 'RAZORPAY':
            try:
                client = razorpay.Client(auth=("rzp_test_MAimzLa32DUYt6", "qbDDZBXaEQPNG72T9ZPVPytC"))
                amount_in_paise = int(total_price * 100)  # Convert INR to paise
                razorpay_order = client.order.create({
                    'amount': amount_in_paise,
                    'currency': 'INR',
                    'payment_capture': '1'
                })
                order.razorpay_order_id = razorpay_order.get('id')
                order.save()

                # Redirect to a payment page where Razorpay checkout is initialized
                return redirect('initiate_payment', order_id=order.id)
            except Exception as e:
                messages.error(request, "Error creating payment order: " + str(e))
                order.delete()  # Optionally, delete the order if payment creation fails
                return redirect('checkoutpage')

        # **For COD or other payment methods, redirect to order confirmation**
        return redirect('order_confirmation', order_id=order.id)

    return redirect('checkoutpage')


# @login_required
# def place_order(request):
#     if request.method == 'POST':
#         address_id = request.POST.get('address_id')
#         payment_option = request.POST.get('payment_option')

#         if not address_id:
#             messages.error(request, "Please select an address before placing the order.")
#             return redirect('checkoutpage')

#         if not payment_option:
#             messages.error(request, "Please select a payment option.")
#             return redirect('checkoutpage')

#         selected_address = get_object_or_404(Address, id=address_id, user=request.user)
#         cart, created = Cart.objects.get_or_create(user=request.user)
#         cart_items = CartItem.objects.filter(cart=cart)
#         total_price = sum(item.product.price * item.quantity for item in cart_items)

#         if total_price == 0:
#             messages.error(request, "Your cart is empty. Add items before placing the order.")
#             return redirect('checkoutpage')

#         order = Order.objects.create(
#             user=request.user,
#             address=selected_address,
#             total_price=total_price,
#             payment_method=payment_option
#         )

#         for item in cart_items:
#             OrderItem.objects.create(order=order, product=item.product, quantity=item.quantity, price=item.product.price)

#         # ✅ **Assign a unique COD transaction ID**
#         if payment_option == "cash_on_delivery":
#             order.cod_transaction_id = "COD-" + uuid.uuid4().hex[:10]  # Generates a unique ID
#             order.save()

#         # **Handle PayPal Payment**
#         if payment_option == 'PAYPAL':
#             request.session['order_id'] = order.id
#             return redirect('paypal_payment', order_id=order.id)

#         # **Handle Razorpay Payment**
#         if payment_option == 'RAZORPAY':
#             try:
#                 client = razorpay.Client(auth=("rzp_test_MAimzLa32DUYt6", "qbDDZBXaEQPNG72T9ZPVPytC"))
#                 amount_in_paise = int(total_price * 100)
#                 razorpay_order = client.order.create({
#                     'amount': amount_in_paise,
#                     'currency': 'INR',
#                     'payment_capture': '1'
#                 })
#                 order.razorpay_order_id = razorpay_order.get('id')
#                 order.save()

#                 return redirect('initiate_payment', order_id=order.id)
#             except Exception as e:
#                 messages.error(request, "Error creating payment order: " + str(e))
#                 order.delete()
#                 return redirect('checkoutpage')

#         # **For COD or other payment methods, redirect to order confirmation**
#         return redirect('order_confirmation', order_id=order.id)

#     return redirect('checkoutpage')








# @login_required
# def my_orders(request):
#     orders = Order.objects.filter(user=request.user).prefetch_related('order_items__product')
#     order_data = []
#     for order in orders:
#         products = [
#             {
#                 'name': item.product.name,
#                 'price': item.price or item.product.price,
#                 'quantity': item.quantity,
#                 'main_image': item.product.main_image.url if item.product.main_image else 'https://via.placeholder.com/80'
#             }
#             for item in order.order_items.all()
#         ]
#         logger.info(f"Order {order.id} has {order.order_items.count()} items, items={list(order.order_items.values('id', 'product__name', 'quantity'))}")
#         order_data.append({
#             'order': order,
#             'products': products,
#             'transaction_id': order.paypal_transaction_id or order.razorpay_payment_id or 'N/A'
#         })
#     return render(request, 'user/my_order.html', {'orders': order_data})


@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('order_items__product')
    order_data = []

    for order in orders:
        products = [
            {
                'name': item.product.name,
                'price': item.price or item.product.price,
                'quantity': item.quantity,
                'main_image': item.product.main_image.url if item.product.main_image else 'https://via.placeholder.com/80'
            }
            for item in order.order_items.all()
        ]

        logger.info(f"Order {order.id} has {order.order_items.count()} items, items={list(order.order_items.values('id', 'product__name', 'quantity'))}")

        order_data.append({
            'order': order,
            'products': products,
            'transaction_id': order.razorpay_payment_id or 'N/A'  # Removed PayPal reference
        })

    return render(request, 'user/my_order.html', {'orders': order_data})

@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.status not in ['Delivered', 'Cancelled']:  # Only allow cancellation if not already delivered
        order.status = 'Cancelled'
        order.save()
    
    return redirect('my_orders') 
@login_required
def return_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if order.status == "Delivered":
        order.status = "Returned"
        order.save()
        messages.success(request, "Your order has been returned successfully.")
    else:
        messages.error(request, "Order cannot be returned unless it is delivered.")

    return redirect('my_orders')  # Change 'orders_page' to the actual URL name of your orders page

#forgot password

# def custom_password_reset_request(request):
#     form = CustomPasswordResetForm() 
#     if request.method == "POST":
#         email = request.POST.get("email")  # Get email from form input
#         users = User.objects.filter(email=email)

#         if users.exists():
#             user = users.first()
#             uid = urlsafe_base64_encode(force_bytes(user.pk))  # Encode user ID
#             token = default_token_generator.make_token(user)  # Generate token
#             reset_url = f"http://127.0.0.1:8000/reset-password/{uid}/{token}/"  # Change for production

#             # Send email with reset link
#             send_mail(
#                 "Password Reset Request",
#                 f"Click the link to reset your password: {reset_url}",
#                 "noreply@yourdomain.com",
#                 [email],
#                 fail_silently=False,
#             )

#             messages.success(request, "A password reset link has been sent to your email.")
#             return redirect("password_reset_sent")
#         else:
#             messages.error(request, "No account found with this email.")
#             return redirect("password_reset")

#     return render(request, "user/custom_password_reset.html",{"form": form})


# def custom_password_reset_confirm(request, uidb64, token):
#     try:
#         uid = urlsafe_base64_decode(uidb64).decode()
#         user = User.objects.filter(pk=uid).first()  # Use `filter().first()` to avoid errors
#     except (User.DoesNotExist, ValueError):
#         user = None

#     if user and default_token_generator.check_token(user, token):
#         if request.method == "POST":
#             form = SetPasswordForm(user, request.POST)
#             if form.is_valid():
#                 form.save()
                
#                 user.backend = 'django.contrib.auth.backends.ModelBackend'  
#                 login(request, user)  
                
#                 return redirect("password_reset_complete")
#         else:
#             form = SetPasswordForm(user)
#         return render(request, "user/custom_password_reset_confirm.html", {"form": form})
#     else:
#         return render(request, "user/invalid_token.html")
    
    
# # Password Reset Sent View
# def custom_password_reset_sent(request):
#     return render(request, "user/custom_password_reset_sent.html")

# # # Password Reset Complete View
# # def custom_password_reset_complete(request):
# #     return render(request, "user/custom_password_reset_complete.html")
# @login_required
# def custom_password_reset_complete(request):
#     if request.method == 'POST':
#         new_password = request.POST['new_password']
#         user = request.user
#         user.set_password(new_password)
#         user.save()
#         # Update the session to keep the user logged in with the new password
#         update_session_auth_hash(request, user)
#         return render(request, "user/custom_password_reset_complete.html", {'message': 'Password updated successfully.'})
#     return render(request, "user/custom_password_reset_complete.html")

# User = get_user_model()

# def reset_password(request, uidb64, token):
#     try:
#         uid = urlsafe_base64_decode(uidb64).decode()
#         user = User.objects.get(pk=uid)
#     except (TypeError, ValueError, OverflowError, User.DoesNotExist):
#         user = None

#     if user and default_token_generator.check_token(user, token):
#         if request.method == "POST":
#             new_password = request.POST["password"]
#             logout(request)  
            
#             user.set_password(new_password)
#             user.save()

#             user.refresh_from_db()
#             print("New password hash:", user.password)
            
#             return redirect("index")

#         return render(request, "user/reset_password.html", {"valid_link": True})
    
#     return render(request, "user/reset_password.html", {"valid_link": False})






User = get_user_model()

def custom_password_reset_request(request):
    form = CustomPasswordResetForm()
    if request.method == "POST":
        email = request.POST.get("email")
        users = User.objects.filter(email=email)

        if users.exists():
            user = users.first()
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = f"http://127.0.0.1:8000/reset-password/{uid}/{token}/"

            send_mail(
                "Password Reset Request",
                f"Click the link to reset your password: {reset_url}",
                "noreply@yourdomain.com",
                [email],
                fail_silently=False,
            )

            messages.success(request, "A password reset link has been sent to your email.")
            return redirect("password_reset_done")
        else:
            messages.error(request, "No account found with this email.")
            return redirect("password_reset")

    return render(request, "user/custom_password_reset.html", {"form": form})

# def custom_password_reset_confirm(request, uidb64, token):
#     try:
#         uid = urlsafe_base64_decode(uidb64).decode()
#         user = User.objects.get(pk=uid)
#     except (User.DoesNotExist, ValueError):
#         user = None

#     if user and default_token_generator.check_token(user, token):
#         if request.method == "POST":
#             form = SetPasswordForm(user, request.POST)
#             if form.is_valid():
#                 form.save()
                
#                 # Set the backend attribute on the user
#                 user.backend = 'django.contrib.auth.backends.ModelBackend'
                
#                 update_session_auth_hash(request, user)
#                 login(request, user)
#                 return redirect("password_reset_complete")
#         else:
#             form = SetPasswordForm(user)
#         return render(request, "user/custom_password_reset_confirm.html", {"form": form})
#     else:
#         messages.error(request, "The password reset link is invalid.")
#         return redirect("password_reset")








# def custom_password_reset_confirm(request, uidb64, token):
#     try:
#         uid = urlsafe_base64_decode(uidb64).decode()
#         user = User.objects.get(pk=uid)
#     except (User.DoesNotExist, ValueError):
#         user = None

#     if user and default_token_generator.check_token(user, token):
#         if request.method == "POST":
#             form = SetPasswordForm(user, request.POST)
#             if form.is_valid():
#                 form.save()
#                 messages.success(request, "Your password has been successfully reset. You can now log in with your new password.")
#                 return redirect("login")  # Redirect to the login page
#         else:
#             form = SetPasswordForm(user)
#         return render(request, "user/custom_password_reset_confirm.html", {"form": form})
#     else:
#         messages.error(request, "The password reset link is invalid.")
#         return redirect("password_reset")
    
def custom_password_reset_sent(request):
    return render(request, "user/custom_password_reset_sent.html")


def custom_password_reset_confirm(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError):
        user = None

    if user and default_token_generator.check_token(user, token):
        if request.method == "POST":
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()

                messages.success(request, "Your password has been reset successfully. Please log in with your new password.")
                return redirect("login")  # ✅ Redirect to login page instead of logging in automatically
            else:
                print("❌ Form errors:", form.errors)  # Debugging
        else:
            form = SetPasswordForm(user)
        return render(request, "user/custom_password_reset_confirm.html", {"form": form})
    else:
        messages.error(request, "The password reset link is invalid.")
        return redirect("password_reset")






@login_required
def custom_password_reset_complete(request):
    if request.method == 'POST':
        new_password = request.POST['new_password']
        user = request.user
        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)
        return render(request, "user/custom_password_reset_complete.html", {'message': 'Password updated successfully.'})
    return render(request, "user/custom_password_reset_complete.html")

def reset_password(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user and default_token_generator.check_token(user, token):
        if request.method == "POST":
            new_password = request.POST["password"]
            user.set_password(new_password)
            user.save()
            user.refresh_from_db()
            logout(request)
            return redirect("index")
        return render(request, "user/reset_password.html", {"valid_link": True})
    else:
        return render(request, "user/reset_password.html", {"valid_link": False})
#end forgot password










@login_required
def wallet_view(request):
    try:
        wallet = Wallet.objects.get(user=request.user)
    except Wallet.DoesNotExist:
        wallet = Wallet.objects.create(user=request.user)

    transactions = Transaction.objects.filter(wallet=wallet).order_by('-timestamp')
    return render(request, 'user/wallet.html', {'wallet': wallet, 'transactions': transactions})









# def cancel_order(request, order_id):
#     # Get the order from the database
#     order = get_object_or_404(Order, id=order_id)

#     # Ensure the order has a valid payment ID
#     if not order.razorpay_payment_id:
#         messages.error(request, "This order was not paid via Razorpay.")
#         return redirect("order_history")  # Redirect to order history page

#     try:
#         # Convert refund amount to paise (Razorpay uses the smallest currency unit)
#         amount_in_paise = int(order.amount * 100)

#         # Process refund request
#         refund_response = client.payment.refund(order.razorpay_payment_id, {"amount": amount_in_paise})

#         # Update order status in the database
#         order.status = "Cancelled"
#         order.save()

#         messages.success(request, "Your order has been canceled and refunded successfully.")
#         return redirect("order_history")

#     except BadRequestError as e:
#         messages.error(request, f"BadRequestError: {str(e)}")
#     except ServerError as e:
#         messages.error(request, f"ServerError: {str(e)}")
#     except Exception as e:
#         messages.error(request, f"Unexpected Error: {str(e)}")

#     return redirect("my_orders")  # Redirect back in case of errors




#new views.py

# def cancel_order(request, order_id):
#     if request.method == "POST":
#         order = get_object_or_404(Order, id=order_id)

#         # Check payment method (if needed)
#         if not order.razorpay_payment_id:
#             return JsonResponse({"error": "This order was not paid via Razorpay."}, status=400)

#         try:
#             # Update order status
#             order.status = "Cancelled"
#             order.save()

#             return JsonResponse({"success": True, "order_id": order.id, "new_status": order.status})

#         except Exception as e:
#             return JsonResponse({"error": str(e)}, status=500)

#     return JsonResponse({"error": "Invalid request"}, status=400)

logger = logging.getLogger(__name__)

@login_required
def cancel_order(request, order_id):
    if request.method == "POST":
        order = get_object_or_404(Order, id=order_id)

        if not order.razorpay_payment_id:
            return JsonResponse({"error": "This order was not paid via Razorpay."}, status=400)

        try:
            with transaction.atomic():  # Ensures database consistency
                # Update order status
                order.status = "Cancelled"
                order.save()

                # Get or create wallet
                wallet, created = Wallet.objects.get_or_create(user=order.user)

                # Refund the order amount to the wallet
                refund_amount = order.total_price  # Corrected field name
                wallet.balance += refund_amount
                wallet.save()

                # Log transaction
                Transaction.objects.create(
                    wallet=wallet,
                    amount=refund_amount,
                    transaction_type="credit"
                )

            return JsonResponse({"success": True, "order_id": order.id, "new_status": order.status, "wallet_balance": wallet.balance})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)

#end new views.py




# @csrf_exempt  # Remove this if CSRF token is properly passed


def product_offers(request):
    offers = ProductOffer.objects.filter(start_date__lte=now, end_date__gte=now)
    return render(request, 'offers/product_offers.html', {'offers': offers})

def category_offers(request):
    offers = CategoryOffer.objects.filter(start_date__lte=now, end_date__gte=now)
    return render(request, 'offers/category_offers.html', {'offers': offers})

def referral_offers(request):
    offers = ReferralOffer.objects.filter(status='active')
    return render(request, 'offers/referral_offers.html', {'offers': offers})



def create_order(request):
    if request.method == "POST":
        amount = 50000  # Example amount
        currency = 'INR'
        receipt = 'order_rcptid_11'  # Unique receipt ID

        try:
            payment = client.order.create({
                'amount': amount,
                'currency': currency,
                'receipt': receipt,
                'payment_capture': '1'
            })

            # Get user and address information
            user = request.user
            address = user.address_set.first()  # Example: get first address for the user
            items = user.cart_items.all()  # Example: get all items in the user's cart
            total_price = sum(item.product.price for item in items)  # Calculate total price

            # Save order details to database
            order = Order(
                user=user,
                address=address,
                total_price=total_price,
                payment_method='RAZORPAY',
                status='Pending',
                razorpay_order_id=payment['id'],
                payment_status=payment['status']
            )
            order.save()
            order.items.set(items)  # Associate items with the order

            return render(request, 'user/payment.html', {'payment': payment})
        except razorpay.errors.RazorpayError as e:
            print(f"Razorpay Error: {str(e)}")
            return render(request, 'user/error.html', {'error': str(e)})

    return





    


@csrf_exempt
def verify_payment(request):
    if request.method == "POST":
        data = request.POST
        try:
            razorpay.Client.utility.verify_payment_signature(data)
            # Update order status to 'paid'
            return JsonResponse({'status': 'success'})
        except:
            # Handle the error
            return JsonResponse({'status': 'failure'})
        

def order_success(request):
    return render(request, 'user/order_success.html')



# def generate_invoice_data(order_id):
#     from products.models import Order  # Import your Order model

#     try:
#         order = Order.objects.get(id=order_id)
#     except Order.DoesNotExist:
#         return None

#     invoice_data = {
#         'order_id': order.id,
#         'customer_name': order.user.username,
#         'payment_method': order.payment_method,
#         'total_price': order.total_price,
#         'shipping_address': f"{order.address.first_name} {order.address.last_name}, "
#                             f"{order.address.house_no}, {order.address.street_address}, "
#                             f"{order.address.city}, {order.address.region}, {order.address.postcode}",
#         'delivery_date': order.delivery_date,
#         'order_items': order.order_items.all()  # Fix: Using correct related_name
#     }

#     return invoice_data
# config = pdfkit.configuration(wkhtmltopdf="C:\\Users\jayas\Downloads\wkhtmltox-0.12.6-1.msvc2015-win64.exe")

# def download_invoice(request, order_id):
#     invoice_data = generate_invoice_data(order_id)
#     if not invoice_data:
#         return HttpResponse("Order not found", status=404)

#     html = render_to_string('user/invoice_template.html', {'invoice_data': invoice_data})
    
#     # Convert HTML to PDF
#     pdf = pdfkit.from_string(html, False)

#     response = HttpResponse(pdf, content_type='application/pdf')
#     response['Content-Disposition'] = f'attachment; filename="invoice_{order_id}.pdf"'
#     return response

WKHTMLTOPDF_PATH = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"

# Ensure the executable exists
if not os.path.exists(WKHTMLTOPDF_PATH):
    raise FileNotFoundError(f"wkhtmltopdf not found at: {WKHTMLTOPDF_PATH}")

# Configure pdfkit
config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)

def generate_invoice_data(order_id):
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return None

    invoice_data = {
        'order_id': order.id,
        'customer_name': order.user.username,
        'payment_method': order.payment_method,
        'total_price': order.total_price,
        'shipping_address': f"{order.address.first_name} {order.address.last_name}, "
                            f"{order.address.house_no}, {order.address.street_address}, "
                            f"{order.address.city}, {order.address.region}, {order.address.postcode}",
        'delivery_date': order.delivery_date,
        'order_items': order.order_items.all()  # Fix: Using correct related_name
    }

    return invoice_data

def download_invoice(request, order_id):
    invoice_data = generate_invoice_data(order_id)
    if not invoice_data:
        return HttpResponse("Order not found", status=404)

    html = render_to_string('user/invoice_template.html', {'invoice_data': invoice_data})
    
    # Convert HTML to PDF (Fix: Pass `configuration=config`)
    pdf = pdfkit.from_string(html, False, configuration=config)

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order_id}.pdf"'
    return response



def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)
    response = HttpResponse(content_type='application/pdf')
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('We had some errors <pre>' + html + '</pre>')
    return response









def calculate_delivery_charge(address):
    # Example fixed charge
    fixed_charge = 50

    # Define postal code-based charges
    postal_code_based_charges = {
        '678621': 50,
        '682006': 60,
    }

    # Get the delivery charge based on the postal code or use the fixed charge if the postal code is not found
    delivery_charge = postal_code_based_charges.get(address.postcode, fixed_charge)

    return delivery_charge



def payment_failed(request):
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        order = get_object_or_404(Order, id=order_id)
        order.payment_status = 'Payment Pending'
        order.save()
        return JsonResponse({'message': 'Order payment status updated to Payment Pending.'})
    else:
        return JsonResponse({'message': 'Invalid request method.'}, status=400)
    








@csrf_exempt
@login_required
def payment_callback(request):
    if request.method == "POST":
        payment_data = request.POST
        try:
            client = razorpay.Client(auth=("rzp_test_MAimzLa32DUYt6", "qbDDZBXaEQPNG72T9ZPVPytC"))

            # Verify payment signature
            params_dict = {
                'razorpay_order_id': payment_data['razorpay_order_id'],
                'razorpay_payment_id': payment_data['razorpay_payment_id'],
                'razorpay_signature': payment_data['razorpay_signature']
            }
            client.utility.verify_payment_signature(params_dict)

            # Update order status and payment details
            order = Order.objects.get(razorpay_order_id=payment_data['razorpay_order_id'])
            order.razorpay_payment_id = payment_data['razorpay_payment_id']
            order.payment_status = 'Paid'
            order.status = 'Processing'
            order.save()

            messages.success(request, "Payment successful!")
            return redirect('order_confirmation', order_id=order.id)

        except (razorpay.errors.SignatureVerificationError, Order.DoesNotExist) as e:
            messages.error(request, "Payment verification failed or order not found.")
            return redirect('checkoutpage')

    return redirect('checkoutpage')




paypalrestsdk.configure({
    "mode": "sandbox",  # or "live"
    "client_id": "AUIZsWRO2Snvs5c55uP7Zpx8ROSc-TSAwfAGtXrAwXu8gz3dl_lVjzAKDfLgPL0r0f4bb7URRTbTUlHA",
    "client_secret": "EOyoBk9CPLjDvinZfn1531ZsDDTCugVYI-MywCCQKdeS_ArvEYvyqumZMZF3DEcabqlX8Bsjiqd3XUBD"
})
    

@login_required
def create_paypal_payment(request):
    if request.method == 'POST':
        final_price = request.POST.get('final_price')
        address_id = request.POST.get('address_id')
        address = get_object_or_404(Address, id=address_id, user=request.user)
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items = CartItem.objects.filter(cart=cart)

        if not cart_items.exists():
            logger.error("Cart is empty")
            messages.error(request, "Your cart is empty! Please add products before proceeding.")
            return redirect('checkoutpage')

        if not address.city:
            address.city = "Default City"
            address.save()

        # Create Order and OrderItems within a transaction
        with transaction.atomic():
            order = Order(
                user=request.user,
                address=address,
                total_price=final_price,
                status='Pending',
                payment_method='PAYPAL'
            )
            order.save()

            for item in cart_items:
                try:
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        price=item.product.price
                    )
                except Exception as e:
                    logger.error(f"Failed to create OrderItem for order {order.id}, product {item.product.id}: {e}")
                    raise

            logger.info(f"Created order {order.id} with {cart_items.count()} items")

            # Calculate item subtotal and add delivery charge
            item_subtotal = sum(float(item.product.price) * item.quantity for item in cart_items)
            delivery_charge = float(final_price) - item_subtotal  # Extract delivery charge

            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {"payment_method": "paypal"},
                "redirect_urls": {
                    "return_url": request.build_absolute_uri(reverse('payment_success') + f'?order_id={order.id}'),
                    "cancel_url": request.build_absolute_uri(reverse('payment_cancel'))
                },
                "transactions": [{
                    "item_list": {
                        "items": [
                            {"name": item.product.name, "sku": str(item.product.id), "price": str(item.product.price), "currency": "INR", "quantity": item.quantity}
                            for item in cart_items
                        ] + [
                            {"name": "Delivery Charge", "sku": "DELIVERY", "price": str(delivery_charge), "currency": "INR", "quantity": 1}
                        ],
                        "shipping_address": {
                            "recipient_name": f"{address.first_name} {address.last_name}",
                            "line1": address.street_address,
                            "line2": address.house_no,
                            "city": address.city,
                            "state": address.region,
                            "postal_code": address.postcode,
                            "country_code": "IN"
                        }
                    },
                    "amount": {
                        "total": str(final_price),
                        "currency": "USD"  # Changed from "USD" to "INR"
                    },
                    "description": "Payment for order"
                }]
            })

            if payment.create():
                order.paypal_payment_id = payment.id
                order.save()
                logger.info(f"PayPal payment created for order {order.id}: {payment.id}")
                request.session['order_id'] = order.id
                for link in payment.links:
                    if link.method == "REDIRECT":
                        return redirect(link.href)
            else:
                logger.error(f"PayPal payment creation failed: {payment.error}")
                messages.error(request, f"Error processing PayPal payment: {payment.error}")
                order.delete()
                return redirect('checkoutpage')
    return redirect('checkoutpage')



@login_required
def paypal_success(request):
    payment_id = request.GET.get('paymentId')
    payer_id = request.GET.get('PayerID')
    order_id = request.GET.get('order_id') or request.session.get('order_id')

    if not (payment_id and payer_id and order_id):
        messages.error(request, "Missing payment or order information!")
        logger.error(f"PayPal success called with incomplete data: paymentId={payment_id}, payerId={payer_id}, order_id={order_id}")
        return redirect('payment_failure')

    try:
        payment = paypalrestsdk.Payment.find(payment_id)
        logger.info(f"Payment fetched: {payment.to_dict()}")

        if payment.execute({"payer_id": payer_id}):
            order = get_object_or_404(Order, id=order_id, user=request.user)
            with transaction.atomic():
                order.status = 'Paid'
                order.payment_status = 'Completed'
                order.paypal_transaction_id = payment_id
                order.transaction_details = payment.to_dict()
                order.reduce_stock()  # This should work if order_items are present
                order.save()

            logger.info(f"Order {order.id} updated: payment_status={order.payment_status}, items count={order.order_items.count()}, items={list(order.order_items.values('id', 'product__name', 'quantity'))}")
            CartItem.objects.filter(cart__user=request.user).delete()
            return render(request, 'user/payment_success.html', {
                'order': order,
                'transaction_id': payment_id,
                'payment_method': 'PayPal',
                'payment_state': payment.state,
                'payer_id': payer_id,
            })
        else:
            messages.error(request, "Payment execution failed!")
            logger.error(f"Payment execution failed: {payment.error}")
            return redirect('payment_failure')
    except Exception as e:
        messages.error(request, f"Error processing payment: {str(e)}")
        logger.error(f"Payment processing error: {str(e)}", exc_info=True)
        return redirect('payment_failure')

def payment_cancel(request):
    return render(request, 'user/payment_cancel.html')


def payment_failure(request):
    return render(request, 'user/payment_failure.html')


@login_required
def retry_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # Use the original order items to calculate the total cost
    order_items = OrderItem.objects.filter(order=order)
    if not order_items.exists():
        messages.error(request, "No items found for this order.")
        return redirect('my_orders')

    # Calculate total cost based on the original order items
    total_cost = sum(item.quantity * item.price for item in order_items)
    discount_amount = order.discount_amount or 0
    final_price = total_cost - discount_amount

    # Convert final price to paise for Razorpay
    amount_in_paise = int(float(final_price) * 100)

    try:
        # Create Razorpay client instance
        client = razorpay.Client(auth=("rzp_test_MAimzLa32DUYt6", "qbDDZBXaEQPNG72T9ZPVPytC"))

        # Create Razorpay order
        order_data = {
            "amount": amount_in_paise,
            "currency": "INR",
            "payment_capture": "1",  # Automatic capture
        }
        razorpay_order = client.order.create(order_data)
        logger.debug(f"Order created successfully for retry: {razorpay_order}")

        # Update Django Order with new Razorpay order ID
        order.razorpay_order_id = razorpay_order["id"]
        order.payment_status = 'Pending'
        order.save()

        context = {
            "amount": amount_in_paise,
            "order_id": razorpay_order["id"],
            "razorpay_key": 'rzp_test_MAimzLa32DUYt6',
            "callback_url": request.build_absolute_uri('/payment/payment-status/'),
        }
        return render(request, "user/payment.html", context)

    except razorpay.errors.BadRequestError as bad_request_error:
        logger.error(f"Bad request error (possibly authentication): {bad_request_error}")
        messages.error(request, "Payment initiation failed: " + str(bad_request_error))
        return redirect('my_orders')
    except AttributeError as attr_error:
        logger.error(f"AttributeError in Razorpay client: {attr_error}")
        messages.error(request, "Razorpay configuration error: " + str(attr_error))
        return redirect('my_orders')
    except Exception as e:
        logger.error(f"Error occurred during payment retry: {e}")
        messages.error(request, "An error occurred during payment retry: " + str(e))
        return redirect('my_orders')



def view_order_details(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'user/order_details.html', {'order': order})

def track_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'user/track_order.html', {'order': order})
