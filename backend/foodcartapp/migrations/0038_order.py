# Generated by Django 3.2.15 on 2023-08-02 14:36

from django.db import migrations, models
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    dependencies = [
        ('foodcartapp', '0037_auto_20210125_1833'),
    ]

    operations = [
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('client_firstname', models.CharField(default='', max_length=100, verbose_name='имя')),
                ('client_lastname', models.CharField(default='', max_length=100, verbose_name='фамилия')),
                ('phone', phonenumber_field.modelfields.PhoneNumberField(db_index=True, default='', max_length=128, region=None, verbose_name='телефон')),
                ('created_at', models.DateTimeField(db_index=True, verbose_name='дата и время заказа')),
                ('products', models.ManyToManyField(to='foodcartapp.Product', verbose_name='товары')),
            ],
            options={
                'verbose_name': 'заказ',
                'verbose_name_plural': 'заказы',
            },
        ),
    ]