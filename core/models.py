# =========================================
# file: core/models.py
# =========================================
import hashlib
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class Department(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self) -> str:
        return self.name


class Supervisor(models.Model):
    name = models.CharField(max_length=255, db_index=True)

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

    title = models.TextField(blank=True)

    title_hash = models.CharField(
        max_length=64,
        db_index=True,
        editable=False,
        default="",
        blank=True,
        verbose_name="بصمة العنوان",
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="researches",
        verbose_name="قسم الباحث",
    )

    degree = models.CharField(max_length=10, choices=Degree.choices, db_index=True)

    researcher_type = models.CharField(
        max_length=20,
        choices=ResearcherType.choices,
        default=ResearcherType.RESEARCHER,
        db_index=True,
        verbose_name="النوع",
    )

    # ✅ رقم الهاتف
    phone = models.CharField("رقم الهاتف", max_length=20, blank=True, null=True)

    # ✅ التواريخ (مرة واحدة وبأسماء موحدة)
    registration_date = models.DateField("تاريخ التسجيل", blank=True, null=True)
    frame_date = models.DateField("تاريخ الإطار", blank=True, null=True)
    university_approval_date = models.DateField("تاريخ موافقة الجامعة", blank=True, null=True)

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
        t = (self.title or "").strip()
        self.title_hash = hashlib.sha256(t.encode("utf-8")).hexdigest() if t else ""
        super().save(*args, **kwargs)

    # =========================
    # المصروفات السنوية (Helpers)
    # =========================
    def _prefetched_fee_payments(self):
        cache = getattr(self, "_prefetched_objects_cache", {})
        return cache.get("fee_payments")

    def get_fees_status(self, year: int) -> str:
        """
        يرجع: 'paid' أو 'unpaid'
        """
        pref = self._prefetched_fee_payments()
        if pref is not None:
            for p in pref:
                if p.year == int(year):
                    return "paid" if p.is_paid else "unpaid"
            return "unpaid"

        p = self.fee_payments.filter(year=int(year)).first()
        return "paid" if (p and p.is_paid) else "unpaid"

    def get_current_year_fees_status(self) -> str:
        year = timezone.localdate().year
        return self.get_fees_status(year)

    # ==================================================
    # Backward-compat properties (لا تحتاج Migration)
    # ==================================================
    @property
    def fees_paid(self) -> bool:
        """حالة مصروفات السنة الحالية كـ True/False (بديل fees_paid القديم)."""
        return self.get_current_year_fees_status() == "paid"

    @property
    def fees_paid_at(self):
        """تاريخ دفع مصروفات السنة الحالية (بديل fees_paid_at القديم)."""
        year = timezone.localdate().year
        p = self.fee_payments.filter(year=int(year)).first()
        return p.paid_at if (p and p.is_paid) else None

    class Meta:
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


class ResearchFeePayment(models.Model):
    """
    ✅ مصروفات سنوية لكل باحث
    - لكل (باحث + سنة) سجل واحد
    """
    research = models.ForeignKey(
        Research,
        on_delete=models.CASCADE,
        related_name="fee_payments",
        verbose_name="الباحث",
    )
    year = models.PositiveIntegerField("السنة")
    is_paid = models.BooleanField("تم الدفع", default=False)
    paid_at = models.DateTimeField("تاريخ الدفع", blank=True, null=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["research", "year"], name="uniq_research_fee_year"),
        ]
        ordering = ["-year"]

    def mark_paid(self):
        self.is_paid = True
        self.paid_at = timezone.now()
        self.save(update_fields=["is_paid", "paid_at", "updated_at"])

    def mark_unpaid(self):
        self.is_paid = False
        self.paid_at = None
        self.save(update_fields=["is_paid", "paid_at", "updated_at"])

    def __str__(self):
        return f"{self.research} - {self.year} - {'Paid' if self.is_paid else 'Unpaid'}"


class DepartmentUser(models.Model):
    """
    Extensions to the User model to link a user to a specific Department.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='department_user')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='users')

    def __str__(self):
        return f"{self.user.username} - {self.department.name}"
