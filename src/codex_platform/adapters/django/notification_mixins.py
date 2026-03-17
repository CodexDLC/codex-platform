"""
codex_platform.adapters.django.notification_mixins
==================================================
Django-миксины для моделей контента.

Предоставляет готовую структуру полей для хранения текстовых блоков
уведомлений в базе данных Django.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class BaseEmailContentMixin(models.Model):
    """
    Абстрактная модель для хранения блоков контента писем.

    Поля:
        key: Уникальный код блока (например, 'bk_confirmation_body').
        category: Группировка (Booking, Contacts и т.д.).
        text: Сам текст (поддерживает переводы через modeltranslation).
        description: Внутренняя заметка для администратора.
    """

    CATEGORY_CHOICES = [
        ("general", _("General / Shared")),
        ("booking", _("Booking System")),
        ("contacts", _("Contact Form / CRM")),
        ("marketing", _("Marketing / Newsletters")),
    ]

    key = models.CharField(_("Key"), max_length=100, unique=True)
    category = models.CharField(_("Category"), max_length=20, choices=CATEGORY_CHOICES, default="general")
    text = models.TextField(_("Text Content"))
    description = models.CharField(_("Description"), max_length=255, blank=True)

    class Meta:
        abstract = True
        ordering = ["category", "key"]

    def __str__(self):
        return f"[{self.category}] {self.key}"
