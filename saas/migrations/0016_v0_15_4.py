# Generated by Django 3.2.16 on 2023-01-04 18:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('saas', '0015_0_11_1'),
    ]

    operations = [
        migrations.AlterField(
            model_name='roledescription',
            name='slug',
            field=models.SlugField(help_text='Unique identifier shown in the URL bar', unique=True),
        ),
    ]
