from django.shortcuts import render,get_list_or_404
from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from products.models import Product,ProductVariant,Category,Order, ProductOffer,CategoryOffer,Coupon,Sales,Order,OrderItem
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required,user_passes_test
from django.db.models import Q
from custom_admin.forms import ProductForm,CategoryForm,ProductVariantForm,ProductOfferForm,CategoryOfferForm
from home.forms import UserUpdateForm, ProfileUpdateForm
from datetime import datetime, timedelta
from django.urls import reverse
from .forms import CouponForm
from django.utils import timezone
from django.core.paginator import Paginator
import io
import xlsxwriter
from reportlab.pdfgen import canvas
from django.http import HttpResponse,JsonResponse
from django.db.models import Sum,Count
import json
from django.views.decorators.csrf import csrf_exempt
import logging
from django.db.models.functions import TruncMonth, TruncYear
from datetime import datetime, timedelta
from products.models import Category 
from home.models import Address
from django.utils.timezone import now
from collections import Counter
from reportlab.lib.pagesizes import letter






# Create your views here
 

def signin(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_superuser:
                login(request, user)
                return redirect('custom_admin:index')  
            else:
                messages.error(request, 'You do not have permission to access the admin panel.')
                return redirect('home')  
            
       
        messages.error(request, 'Invalid credentials.')
        return redirect('custom_admin:signin')  
    
    return render(request, 'custom_admin/signin.html')



def home(request):
    return render(request, 'home.html') 


def products_view(request):
    query = request.GET.get('query', '')
    
    if query:
        products = Product.objects.filter(name__icontains=query)
    else:
        products = Product.objects.all()
    
    context = {
        'products': products,
        'query': query,
    }
    return render(request, 'custom_admin/products_view.html', context)


  
    

def products_details(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return render(request, 'user/404.html', status=404)  
    return render(request, 'user/products_details.html', {'product': product})


def index(request):
    return render(request,'custom_admin/index.html') 


def superuser_required(view_func):
    decorated_view_func = user_passes_test(
        lambda u: u.is_superuser,
        login_url='custom_admin:signin'  
    )(view_func)
    return decorated_view_func

@superuser_required
@login_required
def user_management(request):
    query = request.GET.get('search', '')  
    if query:
        users = User.objects.exclude(is_superuser=True).filter(
            Q(username__icontains=query) | Q(email__icontains=query)  
        )
    else:
        users = User.objects.exclude(is_superuser=True)  

    return render(request, 'custom_admin/users.html', {
        'users': users,
        'search_query': query,  
    })

@superuser_required
@login_required
def block_unblock_user(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        
        try:
            user = User.objects.get(id=user_id)
            if action == 'block':
                user.is_active = False
                messages.success(request, f'User {user.username} has been blocked.')
            elif action == 'activate':
                user.is_active = True
                messages.success(request, f'User {user.username} has been activated.')
            user.save()
        except User.DoesNotExist:
            messages.error(request, 'User does not exist.')
    
    return redirect('custom_admin:users')



@superuser_required
@login_required
def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    profile = user.profile  

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, f"User {user.username} updated successfully.")
            return redirect('custom_admin:users')

    else:
        user_form = UserUpdateForm(instance=user)
        profile_form = ProfileUpdateForm(instance=profile)

    return render(request, 'custom_admin/edit_user.html', {
        'user_form': user_form,
        'profile_form': profile_form,
    })





















def add_product(request):
    print("Request Method:", request.method)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        print("POST data:", request.POST)
        print("FILES data:", request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Product added successfully!")
            print("Form is valid")
            return redirect('custom_admin:products_view')  
        else:
            print("Form errors:", form.errors)
    else:
        form = ProductForm()
    return render(request, 'custom_admin/add_product.html', {'form': form})


def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Product updated successfully!")
            return redirect('custom_admin:products_view')  # Adjust URL as needed
        else:
            print(form.errors)

    else:
        form = ProductForm(instance=product)
    return render(request, 'custom_admin/edit_product.html', {'form': form})


def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        product.delete()
        return redirect('custom_admin:products_details', product_id=product.id)
    return render(request, 'custom_admin/delete_product.html', {'product': product})

def productmanagement(request):
    return render(request,'custom_admin/productmanagement.html')

def product_view(request):
    return render(request,'custom_Admin/products_view.html')

def category_list(request):
    categories = Category.objects.all()
    return render(request, 'custom_admin/category_list.html', {'categories': categories})


def add_category(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Category added successfully!")
            return redirect('custom_admin:category_list')
    else:
        form = CategoryForm()
    return render(request, 'custom_admin/add_category.html', {'form': form})





def edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Category updated successfully!")
            return redirect('custom_admin:category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'custom_admin/edit_category.html', {'form': form})

def delete_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        category.delete()
        messages.success(request, "Category deleted successfully!")
        return redirect('custom_admin:category_list')
    return render(request, 'custom_admin/delete_category.html', {'category': category})


def add_variant(request):
    if request.method == 'POST':
        form = ProductVariantForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Variant added successfully!")
            return redirect('custom_admin:variant_list')
    else:
        form = ProductVariantForm()
    return render(request, 'custom_admin/add_variant.html', {'form': form})

def variant_list(request):
    variants = ProductVariant.objects.all()
    return render(request, 'custom_admin/variant_list.html', {'variants': variants})




@login_required
def order_list(request):
    orders = Order.objects.all().select_related('user', 'address')
    return render(request, 'custom_admin/order_management.html', {'orders': orders})

@login_required
def order_management(request):
    # orders = Order.objects.all().select_related('user', 'address')
    orders = Order.objects.all().select_related('user', 'address').prefetch_related('order_items__product')
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    orders = paginator.get_page(page_number)
    return render(request, 'custom_admin/order_management.html', {'orders': orders})





def view_order_details(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    # Ensure transaction ID is correctly fetched
    transaction_id = None
    if order.payment_method == "RAZORPAY":
        transaction_id = order.razorpay_payment_id
    elif order.payment_method == "PAYPAL":
        transaction_id = order.paypal_transaction_id

    return render(request, 'custom_admin/order_details.html', {'order': order, 'transaction_id': transaction_id})

# @login_required
# def change_order_status(request, order_id, status):
#     order = get_object_or_404(Order, id=order_id)
#     order.status = status
#     order.save()
#     messages.success(request, f"Order status changed to {status}.")
#     return redirect('custom_admin:order_management')  # Use correct namespacing
@login_required
def change_order_status(request, order_id, status):
    order = get_object_or_404(Order, id=order_id)

    # Prevent status change if order is already cancelled
    if order.status == "Cancelled":
        messages.error(request, "This order was already canceled by the customer. You cannot change its status.")
        return redirect('custom_admin:order_management')

    # Update order status
    order.status = status
    order.save()

    messages.success(request, f"Order status changed to {status}.")
    return redirect('custom_admin:order_management')



def add_offer(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ProductOfferForm(request.POST)
        if form.is_valid():
            offer = form.save(commit=False)
            offer.product = product
            offer.save()
            messages.success(request, f'Offer added to {product.name}.')
            return redirect('custom_admin:products_view')
    else:
        form = ProductOfferForm(initial={'product': product})
    return render(request, 'custom_admin/add_offer.html', {'form': form, 'product': product})


def edit_offer(request, offer_id):
    offer = get_object_or_404(ProductOffer, id=offer_id)
    if request.method == 'POST':
        form = ProductOfferForm(request.POST, instance=offer)
        if form.is_valid():
            form.save()
            messages.success(request, f'Offer for {offer.product.name} updated.')
            return redirect('custom_admin:products_view')
    else:
        form = ProductOfferForm(instance=offer)
    return render(request, 'custom_admin/edit_offers.html', {'form': form, 'offer': offer})






def remove_offer(request, product_id):
    offers = ProductOffer.objects.filter(product_id=product_id)
    
    if not offers.exists():
        messages.error(request, 'No offers found for the specified product.')
        return redirect('custom_admin:products_view')
    
    product_name = offers.first().product.name  # Assuming all offers are for the same product
    for offer in offers:
        offer.delete()
    
    messages.info(request, f'All offers removed from {product_name}.')
    return redirect('custom_admin:products_view')


def add_category_offer(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        form = CategoryOfferForm(request.POST)
        if form.is_valid():
            offer = form.save(commit=False)
            offer.category = category  # Assign the offer to the category
            offer.save()
            messages.success(request, f'Offer added to {category.name}.')
            return redirect('custom_admin:category_list')
    else:
        form = CategoryOfferForm(initial={'category': category})
    return render(request, 'custom_admin/add_category_offer.html', {'form': form, 'category': category})



def edit_category_offer(request, offer_id):
    offer = get_object_or_404(CategoryOffer, id=offer_id)
    
    if request.method == 'POST':
        form = CategoryOfferForm(request.POST, instance=offer)
        if form.is_valid():
            form.save()
            return redirect('category_list') 
    else:
        form = CategoryOfferForm(instance=offer)

    return render(request, 'custom_admin/edit_category_offer.html', {'form': form, 'offer': offer})






def delete_category_offer(request, offer_id):
    offer = get_object_or_404(CategoryOffer, id=offer_id)
    
    if request.method == 'POST':
        # For debugging
        print("Deleting offer:", offer.id)
        offer.delete()
        return redirect('custom_admin:category_list') 
    return render(request, 'custom_admin/delete_category_offer.html', {'offer': offer})


def coupon_management(request):
    coupons = Coupon.objects.all() 
    return render(request, 'custom_admin/coupon_management.html', {'coupons': coupons})

def apply_coupon(request):
    now = timezone.now()
    form = CouponForm(request.POST or None)
    if form.is_valid():
        code = form.cleaned_data['code']
        try:
            coupon = Coupon.objects.get(code=code, valid_from__lte=now, valid_until__gte=now, active=True)
            if coupon.usage_limit > 0:
                request.session['coupon_id'] = coupon.id
                coupon.usage_limit -= 1
                coupon.save()
                return redirect('cart_detail') 
            else:
                form.add_error('code', 'This coupon has reached its usage limit.')
        except Coupon.DoesNotExist:
            form.add_error('code', 'This coupon does not exist or is not valid.')
    return render(request, 'custom_admin/apply_coupon.html', {'form': form})

def remove_coupon(request):
    if 'coupon_id' in request.session:
        del request.session['coupon_id']
    return redirect('cart_detail') 



@login_required
def add_coupon(request):
    if request.method == 'POST':
        form = CouponForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('custom_admin:coupon_management')
    else:
        form = CouponForm()
    return render(request, 'custom_admin/add_coupon.html', {'form': form})



def is_staff(user):
    return user.is_staff
@login_required
@user_passes_test(is_staff)
def edit_coupon(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    if request.method == "POST":
        form = CouponForm(request.POST, instance=coupon)
        if form.is_valid():
            form.save()
            messages.success(request, "Coupon updated successfully.")
            return redirect('custom_admin:coupon_management')
    else:
        form = CouponForm(instance=coupon)
    return render(request, 'custom_admin/edit_coupon.html', {'form': form, 'coupon': coupon})

@login_required
@user_passes_test(is_staff)
def delete_coupon(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    if request.method == "POST":
        coupon.delete()
        messages.success(request, "Coupon deleted successfully.")
        return redirect('custom_admin:coupon_management')
    return render(request, 'custom_admin/delete_coupon.html', {'coupon': coupon})


# def sales_report_view(request):
#     today = datetime.today().date()
#     start_date = request.GET.get('start_date')
#     end_date = request.GET.get('end_date')
#     filter_option = request.GET.get('filter_option')

#     if filter_option == 'daily':
#         orders = Order.objects.filter(created_at__date=today)
#     elif filter_option == 'weekly':
#         start_week = today - timedelta(days=today.weekday())
#         end_week = start_week + timedelta(days=6)
#         orders = Order.objects.filter(created_at__range=[start_week, end_week])
#     elif filter_option == 'yearly':
#         start_year = datetime(today.year, 1, 1).date()
#         end_year = datetime(today.year, 12, 31).date()
#         orders = Order.objects.filter(created_at__range=[start_year, end_year])
#     elif filter_option == 'custom' and start_date and end_date:
#         orders = Order.objects.filter(created_at__range=[start_date, end_date])
#     else:
#         orders = Order.objects.all()

#     # Sales calculations
#     total_sales = sum(order.total_price for order in orders)
#     total_discount = sum(order.discount_amount for order in orders)
#     total_coupons = sum(order.discount_amount for order in orders if order.coupon_code)

#     # Retrieve ordered products and their quantities
#     order_items = OrderItem.objects.filter(order__in=orders)
#     product_counter = Counter()

#     for item in order_items:
#         product_counter[item.product] += item.quantity

#     # Create a list of product details
#     sold_products = [
#         {
#             'name': product.name,
#             'image': product.main_image.url if product.main_image and hasattr(product.main_image, 'url') else None,
#             'quantity_sold': quantity
#         }
#         for product, quantity in product_counter.items()
#     ]

#     context = {
#         'total_sales': total_sales,
#         'total_discount': total_discount,
#         'total_coupons': total_coupons,
#         'filter_option': filter_option,
#         'start_date': start_date,
#         'end_date': end_date,
#         'sold_products': sold_products
#     }

#     return render(request, 'custom_admin/salesReport.html', context)


# def generate_pdf(context):
#     buffer = io.BytesIO()
#     p = canvas.Canvas(buffer, pagesize=letter)

#     # Starting position
#     y_position = 750  

#     p.setFont("Helvetica", 12)
#     p.drawString(100, y_position, "Sales Report")

#     y_position -= 30  # Move down
#     p.drawString(100, y_position, f"Total Sales: ₹{context['total_sales']}")

#     y_position -= 20
#     p.drawString(100, y_position, f"Total Discounts: ₹{context['total_discount']}")

#     y_position -= 20
#     p.drawString(100, y_position, f"Total Coupons Deduction: ₹{context['total_coupons']}")

#     p.showPage()
#     p.save()

#     buffer.seek(0)
#     return buffer



# def generate_excel(context):
#     output = io.BytesIO()
#     workbook = xlsxwriter.Workbook(output)
#     worksheet = workbook.add_worksheet()

#     # Format for bold headers
#     bold_format = workbook.add_format({'bold': True})

#     # Write headers
#     worksheet.write('A1', 'Metric', bold_format)
#     worksheet.write('B1', 'Amount', bold_format)

#     # Write data
#     data = [
#         ("Total Sales", context['total_sales']),
#         ("Total Discounts", context['total_discount']),
#         ("Total Coupons Deduction", context['total_coupons']),
#     ]

#     row = 1
#     for metric, amount in data:
#         worksheet.write(row, 0, metric)
#         worksheet.write(row, 1, amount)
#         row += 1

#     # Auto-adjust column width
#     worksheet.set_column('A:A', 25)  
#     worksheet.set_column('B:B', 15)  

#     workbook.close()
#     output.seek(0)
#     return output









# def download_report(request, report_type):
#     context = {
#         'total_sales': 50000,
#         'total_discount': 5000,
#         'total_coupons': 2000,
#     }

#     if report_type == "pdf":
#         pdf_file = generate_pdf(context)
#         response = HttpResponse(pdf_file, content_type='application/pdf')
#         response['Content-Disposition'] = 'attachment; filename="sales_report.pdf"'
#         return response

#     elif report_type == "excel":
#         excel_file = generate_excel(context)
#         response = HttpResponse(excel_file, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
#         response['Content-Disposition'] = 'attachment; filename="sales_report.xlsx"'
#         return response

#     return HttpResponse("Invalid report type", status=400)



def generate_pdf(context):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)

    y_position = 750

    p.setFont("Helvetica", 12)
    p.drawString(100, y_position, "Sales Report")

    y_position -= 30
    p.drawString(100, y_position, f"Total Sales: ₹{context['total_sales']}")

    y_position -= 20
    p.drawString(100, y_position, f"Total Discounts: ₹{context['total_discount']}")

    y_position -= 20
    p.drawString(100, y_position, f"Total Coupons Deduction: ₹{context['total_coupons']}")

    y_position -= 30
    p.drawString(100, y_position, "Products Sold:")

    y_position -= 20
    for product in context['sold_products']:
        p.drawString(100, y_position, f"{product['name']}: {product['quantity_sold']} sold")
        y_position -= 20

    p.showPage()
    p.save()

    buffer.seek(0)
    return buffer




def generate_excel(context):
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()

    bold_format = workbook.add_format({'bold': True})

    worksheet.write('A1', 'Metric', bold_format)
    worksheet.write('B1', 'Amount', bold_format)

    data = [
        ("Total Sales", context['total_sales']),
        ("Total Discounts", context['total_discount']),
        ("Total Coupons Deduction", context['total_coupons']),
    ]

    row = 1
    for metric, amount in data:
        worksheet.write(row, 0, metric)
        worksheet.write(row, 1, amount)
        row += 1

    worksheet.write('A5', 'Products Sold', bold_format)
    row = 5
    for product in context['sold_products']:
        row += 1
        worksheet.write(row, 0, product['name'])
        worksheet.write(row, 1, product['quantity_sold'])

    worksheet.set_column('A:A', 25)
    worksheet.set_column('B:B', 15)

    workbook.close()
    output.seek(0)
    return output





def sales_report_view(request):
    today = datetime.today().date()
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    filter_option = request.GET.get('filter_option')

    if filter_option == 'daily':
        orders = Order.objects.filter(created_at__date=today)
    elif filter_option == 'weekly':
        start_week = today - timedelta(days=today.weekday())
        end_week = start_week + timedelta(days=6)
        orders = Order.objects.filter(created_at__range=[start_week, end_week])
    elif filter_option == 'yearly':
        start_year = datetime(today.year, 1, 1).date()
        end_year = datetime(today.year, 12, 31).date()
        orders = Order.objects.filter(created_at__range=[start_year, end_year])
    elif filter_option == 'custom' and start_date and end_date:
        orders = Order.objects.filter(created_at__range=[start_date, end_date])
    else:
        orders = Order.objects.all()

    total_sales = sum(order.total_price for order in orders)
    total_discount = sum(order.discount_amount for order in orders)
    total_coupons = sum(order.discount_amount for order in orders if order.coupon_code)

    order_items = OrderItem.objects.filter(order__in=orders)
    product_counter = Counter()

    for item in order_items:
        product_counter[item.product] += item.quantity

    sold_products = [
        {
            'name': product.name,
            'image': product.main_image.url if product.main_image and hasattr(product.main_image, 'url') else None,
            'quantity_sold': quantity
        }
        for product, quantity in product_counter.items()
    ]

    context = {
        'total_sales': total_sales,
        'total_discount': total_discount,
        'total_coupons': total_coupons,
        'filter_option': filter_option,
        'start_date': start_date,
        'end_date': end_date,
        'sold_products': sold_products
    }

    if 'download' in request.GET:
        report_type = request.GET.get('download')
        return download_report(request, report_type, context)

    return render(request, 'custom_admin/salesReport.html', context)




def download_report(request, report_type, context):
    if report_type == "pdf":
        pdf_file = generate_pdf(context)
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="sales_report.pdf"'
        return response

    elif report_type == "excel":
        excel_file = generate_excel(context)
        response = HttpResponse(excel_file, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="sales_report.xlsx"'
        return response

    return HttpResponse("Invalid report type", status=400)





def get_sales_data(request):
   
    filter_type = request.GET.get('filter', 'yearly')
    
    # For example purposes, use static/dummy data
    # In production, replace with your own logic and dynamic filtering.
    if filter_type == 'yearly':
        # Group by month for the current year
        data = Sales.objects.filter(date__year=datetime.now().year).values('date__month').annotate(
            total_sales=Sum('amount')
        ).order_by('date__month')
        labels = [str(entry['date__month']) for entry in data]
        values = [entry['total_sales'] for entry in data]
    elif filter_type == 'monthly':
        # Group by day for the current month
        data = Sales.objects.filter(date__year=datetime.now().year, date__month=datetime.now().month).values('date__day').annotate(
            total_sales=Sum('amount')
        ).order_by('date__day')
        labels = [str(entry['date__day']) for entry in data]
        values = [entry['total_sales'] for entry in data]
    elif filter_type == 'weekly':
        # Group by day for the current week (using isoweekday)
        # Note: Adjust the logic as needed (this example uses a simple filter for current week)
        current_week = datetime.now().isocalendar()[1]
        data = Sales.objects.filter(date__week=current_week).values('date__day').annotate(
            total_sales=Sum('amount')
        ).order_by('date__day')
        labels = [str(entry['date__day']) for entry in data]
        values = [entry['total_sales'] for entry in data]
    else:
        labels = []
        values = []

    return JsonResponse({'labels': labels, 'values': values})





def generate_ledger_book(request):
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="ledger_book.pdf"'

    p = canvas.Canvas(response)
    p.drawString(100, 800, "Ledger Book")
   
    p.showPage()
    p.save()
    
    return response








def dashboard(request):
    # Get filter from request (default to 'yearly')
    filter_type = request.GET.get('filter', 'yearly')

    if filter_type == 'yearly':
        date_from = datetime(datetime.now().year, 1, 1)
    elif filter_type == 'monthly':
        date_from = datetime(datetime.now().year, datetime.now().month, 1)
    else:
        date_from = None

    # Get top 5 selling products
    top_selling_products_query = OrderItem.objects.filter(order__created_at__gte=date_from) if date_from else OrderItem.objects.all()
    top_selling_products = list(
        top_selling_products_query
        .values('product__name')
        .annotate(total_sold=Sum('quantity'))
        .order_by('-total_sold')[:5]
    )

    # Get top 5 selling categories
    top_selling_categories_query = Category.objects.annotate(
        total_sold=Sum(
            'products__orderitem__quantity',
            filter=Q(products__orderitem__order__created_at__gte=date_from) if date_from else Q()
        )
    ).values('name', 'total_sold').order_by('-total_sold')[:5]
    top_selling_categories = list(top_selling_categories_query)

    context = {
        'top_selling_products': json.dumps(top_selling_products),
        'top_selling_categories': json.dumps(top_selling_categories),
        'filter_type': filter_type
    }

    return render(request, 'custom_admin/dashboard.html', context)
