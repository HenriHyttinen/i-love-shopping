from django.db import migrations, models


def migrate_cart_currency_to_eur(apps, schema_editor):
    Cart = apps.get_model("commerce", "Cart")
    Cart.objects.filter(currency="USD").update(currency="EUR")


def revert_cart_currency_to_usd(apps, schema_editor):
    Cart = apps.get_model("commerce", "Cart")
    Cart.objects.filter(currency="EUR").update(currency="USD")


class Migration(migrations.Migration):
    dependencies = [
        ("commerce", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cart",
            name="currency",
            field=models.CharField(default="EUR", max_length=8),
        ),
        migrations.RunPython(migrate_cart_currency_to_eur, revert_cart_currency_to_usd),
    ]
