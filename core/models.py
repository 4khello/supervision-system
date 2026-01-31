# =========================================
# file: core/models.py
# =========================================
import hashlib

from django.db import models
from django.utils import timezone


class Department(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self) -> str:
        return self.name


class Supervisor(models.Model):
    name = models.CharField(max_length=255, db_index=True)

    # ✅ القسم في الشيت بتاع "المشرف" (مش الباحث)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supervisors",
        verbose_name="قسم المشرف",
    )

    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class Research(models.Model):
    class Degree(models.TextChoices):
        MA = "MA", "ماجستير"
        PHD = "PHD", "دكتوراه"

    class Status(models.TextChoices):
        REGISTERED = "REGISTERED", "مسجل"
        DISCUSSED = "DISCUSSED", "ناقش/انتهى"
        CANCELLED = "CANCELLED", "إلغاء"
        DISMISSED = "DISMISSED", "فصل"
        OTHER = "OTHER", "أخرى"

    class ResearcherType(models.TextChoices):
        RESEARCHER = "RESEARCHER", "باحث"
        ASSISTANT = "ASSISTANT", "معيد"

    researcher_name = models.CharField(max_length=255, db_index=True)

    # ✅ العنوان طويل: نخليه TextField (بدون index/unique مباشر)
    title = models.TextField(blank=True)

    # ✅ بديل آمن لـ MySQL للـ index/unique: hash ثابت الطول
    # ملاحظة: نخليه blank=True عشان لو العنوان فاضي يبقى hash فاضي بدون مشاكل
    title_hash = models.CharField(
        max_length=64,
        db_index=True,
        editable=False,
        default="",
        blank=True,
        verbose_name="بصمة العنوان",
    )

    # ✅ قسم الباحث (مطلوب يفضل فاضي دلوقتي)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="researches",
        verbose_name="قسم الباحث",
    )

    degree = models.CharField(max_length=10, choices=Degree.choices, db_index=True)

    # ✅ النوع من الشيت: باحث / معيد
    researcher_type = models.CharField(
        max_length=20,
        choices=ResearcherType.choices,
        default=ResearcherType.RESEARCHER,
        db_index=True,
        verbose_name="النوع",
    )

    registration_date = models.DateField(null=True, blank=True)
    frame_date = models.DateField(null=True, blank=True)
    university_approval_date = models.DateField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.REGISTERED,
        db_index=True,
    )
    status_date = models.DateField(null=True, blank=True)
    status_note = models.CharField(max_length=255, blank=True)

    supervisors = models.ManyToManyField(
        Supervisor,
        through="ResearchSupervision",
        related_name="researches",
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """
        ✅ نحسب hash ثابت للعنوان بعد trim.
        - لو العنوان فاضي: نخلي title_hash فاضي (بدل ما نعمل sha256 لنص فاضي)
        """
        t = (self.title or "").strip()
        self.title_hash = hashlib.sha256(t.encode("utf-8")).hexdigest() if t else ""
        super().save(*args, **kwargs)

    class Meta:
        # ✅ يمنع تكرار نفس الباحث/العنوان/المرحلة/النوع حتى لو الشيت مكرر
        # ⚠️ بدل title (TextField) هنستخدم title_hash
        constraints = [
            models.UniqueConstraint(
                fields=["researcher_name", "title_hash", "degree", "researcher_type"],
                name="uniq_research_by_name_titlehash_degree_type",
            )
        ]
        indexes = [
            models.Index(fields=["researcher_name", "degree"]),
            models.Index(fields=["title_hash"]),
        ]

    def __str__(self) -> str:
        t = (self.title or "")[:40]
        return f"{self.researcher_name} - {t}"


class ResearchSupervision(models.Model):
    class Role(models.TextChoices):
        PRIMARY = "PRIMARY", "رئيسي"
        CO = "CO", "مشارك"
        EXTERNAL = "EXTERNAL", "خارجي"

    research = models.ForeignKey(Research, on_delete=models.CASCADE)
    supervisor = models.ForeignKey(Supervisor, on_delete=models.PROTECT)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PRIMARY)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["research", "supervisor"], name="uniq_research_supervisor"),
        ]

    def __str__(self) -> str:
        return f"{self.research_id} -> {self.supervisor} ({self.role})"