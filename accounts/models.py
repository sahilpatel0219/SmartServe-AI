from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Extended user with phone, avatar, email-verification flag."""
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    is_email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'auth_users'

    def __str__(self):
        return self.email or self.username


class Business(models.Model):
    """One business = one isolated workspace. All Mongo data is scoped to business.id."""
    BUSINESS_TYPES = [
        ('restaurant', 'Restaurant'),
        ('cafe', 'Café'),
        ('bakery', 'Bakery'),
        ('food_stall', 'Food Stall'),
        ('cloud_kitchen', 'Cloud Kitchen'),
        ('juice_bar', 'Juice Bar'),
        ('fast_food', 'Fast Food'),
        ('food_truck', 'Food Truck'),
    ]

    name = models.CharField(max_length=200)
    business_type = models.CharField(max_length=30, choices=BUSINESS_TYPES, default='restaurant')
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    gst_number = models.CharField(max_length=20, blank=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    opening_hours = models.JSONField(default=dict, blank=True)
    currency = models.CharField(max_length=5, default='INR')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Businesses'

    def __str__(self):
        return self.name

    @property
    def mongo_id(self) -> str:
        """String ID used as business_id in all MongoDB documents."""
        return str(self.pk)


class Membership(models.Model):
    """Links a User to a Business with a role."""
    ROLES = [
        ('owner', 'Business Owner'),
        ('manager', 'Manager'),
        ('staff', 'Staff'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=ROLES, default='staff')
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'business')

    def __str__(self):
        return f'{self.user.email} @ {self.business.name} ({self.role})'

    @property
    def is_owner(self): return self.role == 'owner'
    @property
    def is_manager(self): return self.role in ('owner', 'manager')


class SubscriptionPlan(models.Model):
    PLAN_NAMES = [
        ('basic', 'Basic'),
        ('pro', 'Pro'),
        ('enterprise', 'Enterprise'),
    ]

    name = models.CharField(max_length=20, choices=PLAN_NAMES, unique=True)
    display_name = models.CharField(max_length=100)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)
    max_users = models.IntegerField(default=3)
    max_menu_items = models.IntegerField(default=50)
    ai_features = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    def __str__(self):
        return f'{self.display_name} — ₹{self.price_monthly}/mo'


class BusinessSubscription(models.Model):
    STATUS = [
        ('active', 'Active'),
        ('trial', 'Trial'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]

    business = models.OneToOneField(Business, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS, default='trial')
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.business.name} — {self.plan.name} ({self.status})'


class LoginHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_history')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    logged_in_at = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=True)

    class Meta:
        ordering = ['-logged_in_at']
