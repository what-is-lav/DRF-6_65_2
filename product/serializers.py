from datetime import date
from decimal import Decimal, InvalidOperation
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Category, Product, Review

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    products_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'products_count']

    def get_products_count(self, category):
        return Product.objects.filter(category=category).count()


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    # Указываем coerce_to_string=False для корректного квантования цены без InvalidOperation
    price = serializers.DecimalField(max_digits=10, decimal_places=2, coerce_to_string=False)

    class Meta:
        model = Product
        fields = '__all__'


class ProductWithReviewsSerializer(serializers.ModelSerializer):
    reviews = ReviewSerializer(many=True, read_only=True)
    rating = serializers.SerializerMethodField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2, coerce_to_string=False)

    class Meta:
        model = Product
        fields = ['id', 'title', 'description', 'price', 'category', 'reviews', 'rating']
        depth = 1

    def get_rating(self, obj):
        reviews = obj.reviews.all()
        count = len(reviews)
        if count > 0:
            total_stars = sum([r.stars for r in reviews if r.stars is not None])
            return round(float(total_stars) / count, 2)
        return None


class CategoryValidateSerializer(serializers.Serializer):
    name = serializers.CharField(required=True, min_length=2, max_length=100)


class ProductValidateSerializer(serializers.Serializer):
    title = serializers.CharField(required=True, min_length=2, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    category = serializers.IntegerField(min_value=1)

    def validate_category(self, category_id):
        try:
            return Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            raise ValidationError('Category does not exist')

    def validate(self, attrs):
        request = self.context.get('request')
        user = getattr(request, 'user', None)

        if not user or not user.is_authenticated:
            raise ValidationError('Пользователь не авторизован.')

        # Безопасное получение пользователя из БД по id
        user_id = getattr(user, 'id', None) or getattr(user, 'user_id', None)
        try:
            db_user = User.objects.get(id=int(user_id))
        except (User.DoesNotExist, TypeError, ValueError):
            raise ValidationError('Пользователь не найден в системе.')

        birthdate = db_user.birthdate

        # 1. Проверка наличия даты рождения
        if not birthdate:
            raise ValidationError('Укажите дату рождения, чтобы создать продукт.')

        # 2. Проверка возраста 18+
        today = date.today()
        age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))

        if age < 18:
            raise ValidationError('Вам должно быть 18 лет, чтобы создать продукт.')

        return attrs


class ReviewValidateSerializer(serializers.Serializer):
    text = serializers.CharField(required=True, min_length=1)
    stars = serializers.IntegerField(min_value=1, max_value=5)
    product = serializers.IntegerField(min_value=1)

    def validate_product(self, product_id):
        try:
            return Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise ValidationError('Product does not exist')