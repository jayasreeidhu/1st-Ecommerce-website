
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile  # Import Profile model
from .models import Wallet

# @receiver(post_save, sender=User)
# def create_or_update_user_profile(sender, instance, created, **kwargs):
#     if created:
#         Profile.objects.create(user=instance)
#     else:
#         # Check if the user has a profile before saving
#         if hasattr(instance, 'profile'):
#             instance.profile.save()
#         else:
#             Profile.objects.create(user=instance) 

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        Wallet.objects.create(user=instance)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()
        else:
            Profile.objects.create(user=instance)
        if hasattr(instance, 'wallet'):
            instance.wallet.save()
        else:
            Wallet.objects.create(user=instance)

