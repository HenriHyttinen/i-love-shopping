from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AddField(
            model_name="category",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name="brand",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AddField(
            model_name="brand",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name="product",
            name="slug",
            field=models.SlugField(blank=True),
        ),
        migrations.AddField(
            model_name="product",
            name="sku",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="product",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="product",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name="productimage",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.CreateModel(
            name="ProductSpec",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=60)),
                ("value", models.CharField(max_length=120)),
                (
                    "product",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="specs", to="catalog.product"),
                ),
            ],
            options={"unique_together": {("product", "key")}},
        ),
    ]
