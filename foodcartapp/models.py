from functools import reduce

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Sum, F
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField


class Restaurant(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    address = models.CharField(
        'адрес',
        max_length=100,
        blank=True,
    )
    contact_phone = models.CharField(
        'контактный телефон',
        max_length=50,
        blank=True,
    )

    class Meta:
        verbose_name = 'ресторан'
        verbose_name_plural = 'рестораны'

    def __str__(self):
        return self.name


class ProductCategory(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def available(self):
        products = (
            RestaurantMenuItem.objects
            .filter(availability=True)
            .values_list('product')
        )
        return self.filter(pk__in=products)


class Product(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    category = models.ForeignKey(
        ProductCategory,
        verbose_name='категория',
        related_name='products',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    image = models.ImageField(
        'картинка'
    )
    special_status = models.BooleanField(
        'спец.предложение',
        default=False,
        db_index=True,
    )
    description = models.TextField(
        'описание',
        max_length=200,
        blank=True,
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = 'товар'
        verbose_name_plural = 'товары'

    def __str__(self):
        return self.name


class RestaurantMenuItemQuerySet(models.QuerySet):
    def available(self):
        restaurant_menu = self.filter(availability=True) \
            .select_related('restaurant', 'product')
        return restaurant_menu


class RestaurantMenuItem(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        related_name='menu_items',
        verbose_name="ресторан",
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='menu_items',
        verbose_name='продукт',
    )
    availability = models.BooleanField(
        'в продаже',
        default=True,
        db_index=True
    )

    objects = RestaurantMenuItemQuerySet.as_manager()

    class Meta:
        verbose_name = 'пункт меню ресторана'
        verbose_name_plural = 'пункты меню ресторана'
        unique_together = [
            ['restaurant', 'product']
        ]

    def __str__(self):
        return f"{self.restaurant.name} - {self.product.name}"


class OrderQuerySet(models.QuerySet):
    def total_amount(self):
        queryset = self.annotate(total_amount=Sum(F('items__quantity') * F('items__price')))
        return queryset

    def active(self):
        queryset = self.exclude(status='delivered')
        return queryset

    def prefetch_items(self):
        prefetch = self.total_amount().exclude(status='delivered').prefetch_related('items')\
            .prefetch_related('items__product')
        return prefetch

    def get_restaurant(self):
        product_restaurant_menu = RestaurantMenuItem.objects.select_related('product', 'restaurant')
        for order in self:
            serialized_restaurants = []
            for order_product in order.items.all():
                serialized_restaurants.append([rest_item.restaurant for rest_item in product_restaurant_menu
                                               if order_product.product_id == rest_item.product.pk])
            cooking_restaurant = reduce(set.intersection, map(set, serialized_restaurants))
            order.cooking_restaurant = cooking_restaurant
        return self

    def get_available_restaurants(self):
        restaurant_menu_items = RestaurantMenuItem.objects.select_related('product', 'restaurant')
        for order in self:
            order_restaurants = []
            for order_product in order.ordered_items.all():
                product_restaurants = set(
                    menu_item.restaurant for menu_item in restaurant_menu_items
                    if order_product.product == menu_item.product and menu_item.availability
                )
                order_restaurants.append(product_restaurants)
            get_available_restaurants = set.intersection(*order_restaurants)
            order.get_available_restaurants = get_available_restaurants
        return self


class Order(models.Model):
    STATUS = (
        ('in_processing', 'В обработке'),
        ('on_assembly', 'На сборке'),
        ('in_delivery', 'В доставке'),
        ('delivered', 'Доставлен')
    )

    PAYMENT = (
        ('cash', "Наличными при доставке"),
        ('online', "Электронно при создании"),
    )

    firstname = models.CharField(
        max_length=100,
        verbose_name='имя',
        default=''
    )
    lastname = models.CharField(
        max_length=100,
        verbose_name='фамилия',
        default=''
    )
    phonenumber = PhoneNumberField(
        verbose_name='телефон',
        db_index=True,
        default=''
    )
    address = models.CharField(
        verbose_name='Адрес доставки',
        max_length=200
    )
    status = models.CharField(
        verbose_name='Статус заказа',
        max_length=20,
        db_index=True,
        choices=STATUS,
        default='in_processing'
    )
    payment = models.CharField(
        verbose_name='Cпособ оплаты',
        max_length=20,
        choices=PAYMENT,
        db_index=True
    )
    comment = models.TextField(
        verbose_name='Комментарий',
        max_length=1000,
        blank=True
    )
    created_date = models.DateTimeField(
        verbose_name="Дата создания",
        default=timezone.now,
        db_index=True
    )
    called_date = models.DateTimeField(
        verbose_name="Дата звонка",
        null=True,
        blank=True
    )
    delivery_date = models.DateTimeField(
        verbose_name="Дата доставки",
        null=True,
        blank=True
    )
    restaurant = models.ForeignKey(
        Restaurant,
        verbose_name='Ресторан, готовящий заказ',
        null=True,
        blank=True,
        related_name='orders',
        on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = 'заказ'
        verbose_name_plural = 'заказы'

    def __str__(self):
        return f"{self.firstname} {self.lastname} - адрес ({self.address})"

    def get_available_restaurants(self):
        available_restaurants = []
        products = [order_item.product for order_item in self.ordered_items.all()]
        menu_items = RestaurantMenuItem.objects.filter(availability=True)

        for menu_item in menu_items:
            if menu_item.product in products:
                available_restaurants[menu_item.restaurant] += 1

        return [restaurant for restaurant, available_products in available_restaurants.items()
                if available_products == len(products)]

    objects = OrderQuerySet.as_manager()


class ProductOrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        related_name='items',
        on_delete=models.CASCADE,
        verbose_name='заказ'
    )
    product = models.ForeignKey(
        Product,
        related_name='orders',
        on_delete=models.CASCADE,
        verbose_name='товар',
    )
    quantity = models.IntegerField(
        verbose_name='количество',
        validators=[MinValueValidator(1), MaxValueValidator(500)]
    )
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    class Meta:
        verbose_name = 'товар в заказе'
        verbose_name_plural = 'товары в заказах'

    def __str__(self):
        return f"{self.product} - кол: {self.quantity}"


class Place(models.Model):
    address = models.CharField(
        verbose_name='Адрес доставки',
        max_length=200,
        unique=True,
    )
    lat = models.DecimalField(
        verbose_name='Широта',
        decimal_places=3,
        max_digits=9,
        blank=True,
        null=True,
    )
    lon = models.DecimalField(
        verbose_name='Долгота',
        decimal_places=3,
        max_digits=9,
        blank=True,
        null=True,
    )

    updated_time = models.DateTimeField(
        'Дата обновления',
        default=timezone.now
    )

    class Meta:
        verbose_name = 'Место'
        verbose_name_plural = 'Места'

    def __str__(self):
        return self.address
