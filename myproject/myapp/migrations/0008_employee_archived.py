# Generated by Django 5.1.2 on 2024-12-14 11:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0007_overtimesetting'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='archived',
            field=models.BooleanField(default=False),
        ),
    ]