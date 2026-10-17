from django.db import models
from django.utils.text import slugify

from core.models import TimeStampedModel


class Category(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    image = models.ImageField(
        upload_to="categories/",
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = [
            "sort_order",
            "name",
        ]

    def __str__(self):
        return self.name


class Product(TimeStampedModel):
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )
    name = models.CharField(max_length=180)
    slug = models.SlugField(unique=True)
    brand = models.CharField(
        max_length=120,
        blank=True,
    )
    sku = models.CharField(
        max_length=80,
        unique=True,
        blank=True,
        help_text="Leave blank to generate a SKU automatically. Existing SKUs remain unchanged when product details are edited.",
    )
    size = models.CharField(
        max_length=80,
        blank=True,
    )
    description = models.TextField(blank=True)
    image = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = [
            "name",
        ]

    def _generate_sku(self):
        """Create a readable, globally unique SKU from product details."""
        parts = (self.brand, self.name, self.size)
        base = slugify("-".join(part.strip() for part in parts if part and part.strip()))
        base = base.upper().strip("-")[:80].rstrip("-") or "PRODUCT"

        candidate = base
        suffix = 2

        queryset = type(self).objects.all()
        if self.pk:
            queryset = queryset.exclude(pk=self.pk)

        while queryset.filter(sku=candidate).exists():
            suffix_text = f"-{suffix}"
            candidate = f"{base[: 80 - len(suffix_text)].rstrip('-')}{suffix_text}"
            suffix += 1

        return candidate

    def save(self, *args, **kwargs):
        generated_sku = not self.sku or not self.sku.strip()
        if generated_sku:
            self.sku = self._generate_sku()

            # Ensure generated SKUs are persisted when callers use update_fields.
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = set(update_fields) | {"sku"}

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
