from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.shortcuts import render, get_object_or_404
from .models import Product,Wishlist
from products.models import Product,ProductVariant,Category,ProductThumbnail
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required,permission_required
from .models import Product, Cart, CartItem,Coupon,Order
from django.utils import timezone
from custom_admin.forms import CouponForm
from .forms import CouponApplyForm
from django.contrib import messages
from django.http import JsonResponse
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now



def products(request):
    category_id = request.GET.get('category_id')
    sort_option = request.GET.get('sort')
    
    if category_id:
        category = get_object_or_404(Category, id=category_id)
        products = Product.objects.filter(category=category).order_by('id')
    else:
        products = Product.objects.all().order_by('id')
        # products = Product.objects.filter(stock__gt=0).order_by('id')

    if sort_option == 'price_low_to_high':
        products = products.order_by('price')
    elif sort_option == 'price_high_to_low':
        products = products.order_by('-price')
    elif sort_option == 'name_asc':
        products = products.order_by('name')
    elif sort_option == 'name_desc':
        products = products.order_by('-name')
    
    paginator = Paginator(products, 9)
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)
    categories = Category.objects.all()
    
    return render(request, 'user/products.html', {'products': products, 'categories': categories})


def product_details(request, product_id):
    product = get_object_or_404(Product, id=product_id) 
    variants = ProductVariant.objects.filter(product=product)

    
    context = {
        'product': product,
        'variants': variants,
        'is_out_of_stock': product.stock == 0
    }
    return render(request, 'user/products_details.html', context)

@login_required
def product_view(request):
    products = Product.objects.all()
    return render(request, 'custom_admin/product_view.html', {'products': products})

def thumbnail_list(request):
    thumbnails = ProductThumbnail.objects.all()
    return render(request, "thumbnails.html", {"thumbnails": thumbnails})


def category_list(request):
    categories = Category.objects.all()
    return render(request, 'custom_Admin/category_list.html', {'categories': categories})


def category_detail(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    products = Product.objects.filter(category=category)
    return render(request, 'user/category_detail.html', {'category': category, 'products': products})




@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    variant_id = request.POST.get("variant_id")

    
    if product.stock == 0:
        return redirect('cart_detail')  

    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)

    if created:
        cart_item.quantity = 1
    else:
        max_quantity_per_person = 5
        new_quantity = min(cart_item.quantity + 1, product.stock, max_quantity_per_person)
        cart_item.quantity = new_quantity

    cart_item.save()
    return redirect('cart_detail')



def cart_detail(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = CartItem.objects.filter(cart=cart)

    # Remove items that are out of stock
    for item in cart_items:
        if item.product.stock == 0:
            item.delete()
    
    # Re-fetch cart items after deletion
    cart_items = CartItem.objects.filter(cart=cart)
    
    total_cost = sum(item.quantity * item.product.price for item in cart_items)
    total_items = sum(item.quantity for item in cart_items)
    
    coupon_form = CouponApplyForm(request.POST or None)
    discount_amount = 0

    coupon_id = request.session.get("coupon_id")
    if coupon_id:
        try:
            coupon = Coupon.objects.get(
                id=coupon_id,
                valid_from__lte=timezone.now(),
                valid_until__gte=timezone.now(),
                usage_limit__gt=0
            )
            discount_amount = (coupon.discount / 100) * total_cost  
            cart.discount_amount = discount_amount  
            cart.coupon_code = coupon.code
            cart.save()
        except Coupon.DoesNotExist:
            del request.session["coupon_id"]  

    final_price = total_cost - discount_amount  

    context = {
        'cart_items': cart_items,
        'total_cost': total_cost,  
        'total_items': total_items,
        'coupon_form': coupon_form,
        'cart': cart,
        'discount_amount': discount_amount, 
        'final_price': final_price,  
    }
    
    return render(request, 'user/cart_detail.html', context)


def get_available_coupons(request):
    """ Return available coupons as JSON """
    coupons = Coupon.objects.filter(valid_from__lte=now(), valid_until__gte=now()).values('id', 'code', 'discount')
    
    return JsonResponse({'coupons': list(coupons)})
# @csrf_exempt
# def update_cart_quantity(request):
#     if request.method == "POST":
#         try:
#             data = json.loads(request.body)
#             item_id = data.get("item_id")
#             quantity = int(data.get("quantity"))

#             cart_item = CartItem.objects.get(id=item_id, cart__user=request.user)

#             # Check stock: if variant exists, use variant stock, else use product stock.
#             stock = cart_item.variant.stock if cart_item.variant else cart_item.product.stock
#             if quantity > stock:
#                 quantity = stock

#             cart_item.quantity = quantity
#             cart_item.save()

#             # Recalculate the total price
#             cart_items = CartItem.objects.filter(cart=cart_item.cart)
#             total_price = sum(item.quantity * item.product.price for item in cart_items)

#             return JsonResponse({"success": True, "total_price": float(total_price)})
#         except Exception as e:
#             return JsonResponse({"success": False, "error": str(e)})

#     return JsonResponse({"success": False, "error": "Invalid request"})
@csrf_exempt
def update_cart_quantity(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            item_id = data.get("item_id")
            quantity = int(data.get("quantity"))

            cart_item = CartItem.objects.get(id=item_id, cart__user=request.user)

            # Check available stock (variant vs product)
            stock = cart_item.variant.stock if cart_item.variant else cart_item.product.stock
            if quantity > stock:
                quantity = stock

            cart_item.quantity = quantity
            cart_item.save()

            # Recalculate total price and total items in the cart
            cart_items = CartItem.objects.filter(cart=cart_item.cart)
            total_price = sum(item.quantity * item.product.price for item in cart_items)
            total_items = sum(item.quantity for item in cart_items)

            return JsonResponse({
                "success": True, 
                "total_price": float(total_price),
                "total_items": total_items
            })
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request"})





@login_required
def remove_from_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item = CartItem.objects.filter(cart=cart, product=product).first()

    if cart_item:
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()

    return redirect('cart_detail')






@login_required
def cart_page(request):
    cart = Cart.objects.get_or_create(user=request.user)
    cart_items = CartItem.objects.filter(cart=cart)

    if request.method == 'POST':
        for item in cart_items:
            quantity = int(request.POST.get(f'quantity-{item.id}', item.quantity))
            if quantity > item.product.stock:
                quantity = item.product.stock

            item.quantity = quantity
            if item.quantity == 0 or item.product.stock == 0:
                item.delete()
            else:
                item.save()

        return redirect('cart_page')  

    total_cost = sum(item.quantity * item.product.price for item in cart_items)
    total_items = sum(item.quantity for item in cart_items)

    return render(request, 'user/cart_detail.html', {
        'cart_items': cart_items,
        'total_cost': total_cost,
        'total_items': total_items
    })



@login_required
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    Wishlist.objects.get_or_create(user=request.user, product=product)
    return redirect('wishlist')

@login_required
def remove_from_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    Wishlist.objects.filter(user=request.user, product=product).delete()
    return redirect('wishlist')

@login_required
def wishlist(request):
    wishlist_items = Wishlist.objects.filter(user=request.user)
    return render(request, 'user/wishlist.html', {'wishlist_items': wishlist_items})

@login_required
def move_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    # Remove the item from the cart (if it exists)
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item = CartItem.objects.filter(cart=cart, product=product).first()
    if cart_item:
        cart_item.delete()
    
    # Add the product to the wishlist if it isn't already there
    wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, product=product)
    if created:
        messages.success(request, f"{product.name} has been added to your wishlist.")
    else:
        messages.info(request, f"{product.name} is already in your wishlist.")
    
    return redirect('cart_detail')


def apply_coupon(request):
    if request.method == "POST":
        form = CouponApplyForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"]
            now = timezone.now()

            try:
                coupon = Coupon.objects.get(
                    code=code,
                    valid_from__lte=now,
                    valid_until__gte=now,
                    usage_limit__gt=0
                )
                request.session["coupon_id"] = coupon.id 
                coupon.usage_limit -= 1
                coupon.save()
                
                print(f" Coupon {coupon.code} applied, new usage limit: {coupon.usage_limit}")  
                
                messages.success(request, f"Coupon '{coupon.code}' applied successfully!")
            except Coupon.DoesNotExist:
                print(" Coupon does not exist or expired.") 
                messages.error(request, "Invalid or expired coupon.")

        return redirect("cart_page")
    
@login_required
@permission_required('yourapp.can_manage_coupons', raise_exception=True)
def coupon_management(request):
    coupons = Coupon.objects.all()
    return render(request, 'user/coupon_management.html', {'coupons': coupons})

@login_required
@permission_required('yourapp.can_view_coupons', raise_exception=True)
def available_coupons(request):
    now = timezone.now()
    coupons = Coupon.objects.filter(valid_from__lte=now, valid_until__gte=now, active=True)
    return render(request, 'user/available_coupons.html', {'coupons': coupons})


@login_required
def remove_coupon(request):
    if "coupon_id" in request.session:
        del request.session["coupon_id"]  # Remove coupon from session
    # Optionally, update the cart instance if you’re storing coupon details in the DB
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart.coupon_code = ""
    cart.discount_amount = 0
    cart.save()
    messages.success(request, "Coupon removed successfully.")
    return redirect("cart_detail")


@login_required
def continue_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.payment_status == 'Failed':
        # Logic to redirect to payment gateway
        return redirect('payment_gateway', order_id=order.id)
    return HttpResponse("Invalid request")


def purchase_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))

    try:
        order = Order.objects.create(product=product, quantity=quantity, user=request.user)
        messages.success(request, 'Purchase successful! Stock updated.')
    except ValueError as e:
        messages.error(request, str(e))

    return redirect('product_detail', product_id=product_id)
