from django import forms
from products.models import Product,ProductVariant,Category, ProductOffer,CategoryOffer,Coupon
from home.models import Profile
from django.contrib.auth.models import User
# ,ProductThumbnail


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'description', 'brand', 'price', 'quantity', 'stock','original_price',
            'discount_percentage', 'stock_status', 'sold', 'main_image', 
            'material', 'dimensions', 'weight', 'warranty','category',
        ]
        # ,ProductThumbnail
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'main_image': forms.ClearableFileInput(),
            
        }
        # 'thumbnail_images': forms.CheckboxSelectMultiple(),
        labels = {
            'name': 'Product Name',
            'description': 'Product Description',
            'main_image': 'Main Product Image',
        }

            
class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']


# Form for the ProductVariant model
class ProductVariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = ['product', 'variant_name', 'variant_value', 'color_image']
        widgets = {
            'color_image': forms.ClearableFileInput(),
        }
        labels = {
            'variant_name': 'Variant Name',
            'variant_value': 'Variant Value (e.g., Color or Size)',
            'color_image': 'Image for Variant (if applicable)',
        }



class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email"]

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["mobile_number"]



class ProductOfferForm(forms.ModelForm):
    class Meta:
        model = ProductOffer
        fields = ['product', 'discount_amount', 'start_date', 'end_date', 'offer_type']
        widgets = {
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

class CategoryOfferForm(forms.ModelForm):
    class Meta:
        model = CategoryOffer
        fields = ['category', 'discount_percentage', 'start_date', 'end_date','offer_type']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = ['code', 'discount', 'valid_from', 'valid_until', 'usage_limit', 'products', 'categories']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }


class SalesReportForm(forms.Form):
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
