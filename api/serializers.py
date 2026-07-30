from rest_framework import serializers
from accounts.models import User, Business, Membership, SubscriptionPlan, BusinessSubscription, LoginHistory


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'phone', 'password']

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value

    def create(self, validated_data):
        import secrets
        password = validated_data.pop('password')
        user = User(username=validated_data['email'], **validated_data)
        user.set_password(password)
        user.email_verification_token = secrets.token_hex(32)
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'phone', 'is_email_verified']


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'email']

    def validate_email(self, value):
        user = self.instance
        if value and User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError('That email is already in use by another account.')
        return value

    def update(self, instance, validated_data):
        email = validated_data.get('email')
        if email and email != instance.email:
            instance.username = email
        return super().update(instance, validated_data)


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = ['name', 'display_name', 'price_monthly', 'max_users', 'max_menu_items', 'ai_features']


class BusinessSubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)

    class Meta:
        model = BusinessSubscription
        fields = ['plan', 'status', 'started_at', 'expires_at']


class BusinessSerializer(serializers.ModelSerializer):
    mongo_id = serializers.CharField(read_only=True)

    class Meta:
        model = Business
        fields = [
            'id', 'mongo_id', 'name', 'business_type', 'address', 'city', 'state',
            'pincode', 'phone', 'email', 'website', 'gst_number', 'opening_hours',
            'currency', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'mongo_id', 'created_at']


class MembershipSerializer(serializers.ModelSerializer):
    business = BusinessSerializer(read_only=True)

    class Meta:
        model = Membership
        fields = ['id', 'business', 'role', 'is_active', 'joined_at']


class LoginHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LoginHistory
        fields = ['ip_address', 'user_agent', 'logged_in_at', 'success']
