# =========================================
# file: core/management/commands/import_supervisions.py
# =========================================
import re
import hashlib
from typing import Iterable, List, Optional

import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from core.models import Department, Supervisor, Research, ResearchSupervision


def normalize_text(x) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    return str(x).strip()


def normalize_spaces(s: str) -> str:
    s = normalize_text(s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def title_to_hash(title: str) -> str:
    t = normalize_spaces(title)
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def map_degree(raw: str) -> str:
    raw = normalize_spaces(raw)
    if any(k in raw.lower() for k in ["دكتور", "دكتورا", "phd", "p.h.d"]):
        return Research.Degree.PHD
    return Research.Degree.MA


def map_researcher_type(raw: str) -> str:
    t = normalize_spaces(raw)
    if "معيد" in t:
        return Research.ResearcherType.ASSISTANT
    return Research.ResearcherType.RESEARCHER


def map_status(raw):
    s = normalize_spaces(raw)
    if not s:
        return Research.Status.REGISTERED, "", None

    if "مسجل" in s:
        return Research.Status.REGISTERED, "", None
    if any(k in s for k in ["ناقش", "مناقش", "نوقش", "تمت المناقشة"]):
        return Research.Status.DISCUSSED, s, None
    if any(k in s for k in ["الغاء", "إلغاء"]):
        return Research.Status.CANCELLED, s, None
    if "فصل" in s:
        return Research.Status.DISMISSED, s, None

    return Research.Status.OTHER, s, None


def split_supervisors(cell: str) -> List[str]:
    """
    ✅ لو الخلية فيها أكتر من مشرف:
    - نفصل على (،) أو , أو ; أو / أو سطر جديد أو " - " أو " و "
    """
    s = normalize_spaces(cell)
    if not s:
        return []
    parts = re.split(r"[،,;/\n]+|\s+-\s+|\s+و\s+", s)
    out = []
    for p in parts:
        p = normalize_spaces(p)
        if p:
            out.append(p)

    # de-dup preserve order
    seen = set()
    uniq = []
    for n in out:
        if n not in seen:
            seen.add(n)
            uniq.append(n)
    return uniq


def find_header_row(raw_df: pd.DataFrame, expected: Iterable[str], max_scan_rows: int = 30) -> Optional[int]:
    expected_set = set(expected)
    for i in range(min(max_scan_rows, len(raw_df))):
        row = raw_df.iloc[i].tolist()
        row_norm = {normalize_spaces(x) for x in row}
        hits = len(expected_set.intersection(row_norm))
        if hits >= 2:
            return i
    return None


class Command(BaseCommand):
    help = "Import Excel (merge duplicates + handle multi-supervisors + supervisor dept + researcher type)."

    def add_arguments(self, parser):
        parser.add_argument("xlsx_path", type=str, help="Path to Excel file")
        parser.add_argument("--sheet", default=None, type=str, help="Excel sheet name (optional)")
        parser.add_argument("--header_row", default=None, type=int, help="0-based header row (optional, auto-detect if omitted)")

        # ✅ أسماء الأعمدة (بعد ما نحدد سطر الهيدر)
        parser.add_argument("--col_degree", default="المرحلة", type=str)
        parser.add_argument("--col_name", default="الإســـــــم", type=str)
        parser.add_argument("--col_title", default="العنـــــــــوان", type=str)
        parser.add_argument("--col_supervisor", default="المشرفين", type=str)

        # ✅ القسم في الشيت = قسم المشرف
        parser.add_argument("--col_supervisor_dept", default="القسم", type=str)

        parser.add_argument("--col_status", default="الحالة", type=str)

        # ✅ النوع (باحث/معيد)
        parser.add_argument("--col_type", default="النوع", type=str)

    @transaction.atomic
    def handle(self, *args, **opts):
        path = opts["xlsx_path"]

        raw = pd.read_excel(path, sheet_name=opts.get("sheet"), header=None)

        expected_cols = [
            opts["col_degree"],
            opts["col_name"],
            opts["col_title"],
            opts["col_supervisor"],
        ]

        header_row = opts.get("header_row")
        if header_row is None:
            header_row = find_header_row(raw, expected_cols)

        if header_row is None:
            raise ValueError(
                "Could not detect header row. Please pass --header_row N (0-based). "
                f"Expected columns like: {expected_cols}"
            )

        header = [normalize_spaces(x) for x in raw.iloc[header_row].tolist()]
        df = raw.iloc[header_row + 1:].copy()
        df.columns = header

        # drop Unnamed columns + empty rows
        df = df.loc[:, ~df.columns.astype(str).str.startswith("Unnamed")]
        df = df.dropna(how="all")

        required = [opts["col_degree"], opts["col_name"], opts["col_title"], opts["col_supervisor"]]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns in Excel: {missing}\nAvailable columns: {list(df.columns)}")

        created_research = 0
        created_supervisors = 0
        created_links = 0
        merged_duplicates = 0

        for _, row in df.iterrows():
            degree_raw = row.get(opts["col_degree"])
            researcher_name = normalize_spaces(row.get(opts["col_name"]))
            title = normalize_spaces(row.get(opts["col_title"]))

            if not researcher_name or not title:
                continue

            supervisors_cell = row.get(opts["col_supervisor"])
            supervisor_names = split_supervisors(supervisors_cell)
            if not supervisor_names:
                continue

            status_raw = row.get(opts["col_status"]) if opts["col_status"] in df.columns else None
            researcher_type_raw = row.get(opts["col_type"]) if opts["col_type"] in df.columns else None
            supervisor_dept_name = normalize_spaces(row.get(opts["col_supervisor_dept"])) if opts["col_supervisor_dept"] in df.columns else ""

            degree = map_degree(degree_raw)
            researcher_type = map_researcher_type(researcher_type_raw)
            status, status_note, status_date = map_status(status_raw)

            # ✅ نستخدم title_hash بدل title في الدمج (حل نهائي لمشكلة MySQL + منع التكرار)
            th = title_to_hash(title)

            # ✅ حاول تجيب Research موجود بالفعل
            qs = Research.objects.filter(
                researcher_name=researcher_name,
                degree=degree,
                researcher_type=researcher_type,
                title_hash=th,
            )

            research = qs.first()

            # ✅ لو فيه duplicates قديمة (قبل تطبيق constraints) هنلمّها ونخلي واحد أساسي
            if qs.count() > 1:
                merged_duplicates += (qs.count() - 1)
                research = qs.order_by("id").first()
                # انقل كل الروابط من المكررات إلى الأساسي
                for dup in qs.exclude(id=research.id):
                    # نقل روابط الاشراف
                    for link in ResearchSupervision.objects.filter(research=dup):
                        ResearchSupervision.objects.get_or_create(
                            research=research,
                            supervisor=link.supervisor,
                            defaults={"role": link.role},
                        )
                    dup.delete()

            if research is None:
                # create جديد
                research = Research.objects.create(
                    researcher_name=researcher_name,
                    title=title,          # save() هيحسب title_hash تلقائيًا
                    degree=degree,
                    researcher_type=researcher_type,
                    department=None,      # ✅ قسم الباحث فاضي
                    registration_date=None,
                    frame_date=None,
                    university_approval_date=None,
                    status=status,
                    status_note=status_note or "",
                    status_date=status_date,
                )
                created_research += 1
            else:
                # ✅ لو العنوان فاضي عنده وده عندنا عنوان -> حدثه
                updated_fields = []
                if (not research.title) and title:
                    research.title = title
                    updated_fields.append("title")

                # ✅ تحديث حالة لو عندنا note وهو فاضي
                if status_note and not research.status_note:
                    research.status = status
                    research.status_note = status_note or ""
                    research.status_date = status_date
                    updated_fields.extend(["status", "status_note", "status_date"])

                if updated_fields:
                    research.save(update_fields=updated_fields + ["updated_at"])

            # ✅ قسم المشرف (من الشيت)
            sup_dept = None
            if supervisor_dept_name:
                sup_dept, _ = Department.objects.get_or_create(name=supervisor_dept_name)

            # ✅ أضف المشرفين (بدون تكرار)
            for sup_name in supervisor_names:
                supervisor, sup_created = Supervisor.objects.get_or_create(name=sup_name)
                if sup_created:
                    created_supervisors += 1

                # خزّن قسم المشرف مرة واحدة (أول مرة)
                if sup_dept and supervisor.department_id is None:
                    supervisor.department = sup_dept
                    supervisor.save(update_fields=["department"])

                link, link_created = ResearchSupervision.objects.get_or_create(
                    research=research,
                    supervisor=supervisor,
                    defaults={"role": ResearchSupervision.Role.PRIMARY},
                )
                if link_created:
                    created_links += 1

        self.stdout.write(self.style.SUCCESS(
            "Done. "
            f"Research created: {created_research} | Supervisors created: {created_supervisors} | "
            f"Links created: {created_links} | Duplicates merged: {merged_duplicates}"
        ))