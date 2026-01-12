from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Brand",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True)),
                ("slug", models.SlugField(unique=True)),
            ],
        ),
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                ("description", models.TextField()),
                ("price", models.DecimalField(decimal_places=2, max_digits=10)),
                ("stock_quantity", models.PositiveIntegerField()),
                ("rating", models.DecimalField(decimal_places=2, default=0, max_digits=3)),
                ("weight_kg", models.DecimalField(decimal_places=2, max_digits=6)),
                ("weight_lb", models.DecimalField(decimal_places=2, max_digits=6)),
                ("length_cm", models.DecimalField(decimal_places=2, max_digits=6)),
                ("width_cm", models.DecimalField(decimal_places=2, max_digits=6)),
                ("height_cm", models.DecimalField(decimal_places=2, max_digits=6)),
                ("length_in", models.DecimalField(decimal_places=2, max_digits=6)),
                ("width_in", models.DecimalField(decimal_places=2, max_digits=6)),
                ("height_in", models.DecimalField(decimal_places=2, max_digits=6)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "brand",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="products", to="catalog.brand"),
                ),
                (
                    "category",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="products", to="catalog.category"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ProductImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="products/")),
                ("alt_text", models.CharField(blank=True, max_length=200)),
                (
                    "product",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="images", to="catalog.product"),
                ),
            ],
        ),
    ]
