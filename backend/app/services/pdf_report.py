"""Generación de informes PDF profesionales (secciones 26-28).

Características:
- Generado en el backend con ReportLab (diseño controlado, apto para imprimir).
- Gráficas creadas con matplotlib e incrustadas como PNG de alta resolución.
- Encabezado con logo configurable (assets/logo.png), pie de página,
  numeración "Página X de Y" y fecha de generación.
- Contenido: resumen general, resumen por dispositivo (tabla con TOTAL),
  gráfica de consumo diario total, gráfica de consumo por dispositivo,
  gráfica de consumo diario por dispositivo, información de tarifas y
  advertencias (días sin tarifa, días sin datos).
- Formato monetario es-CO: $ 1.234.567 — diferenciado de kWh.
"""
from __future__ import annotations

import datetime as dt
import io
import logging
import os
import urllib.request

import matplotlib

matplotlib.use("Agg")  # Sin interfaz gráfica (servidor)
import matplotlib.pyplot as plt  # noqa: E402

from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.pdfgen import canvas as pdfcanvas  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from sqlalchemy import select  # noqa: E402

from app.config import settings  # noqa: E402
from app.models import Device  # noqa: E402
from app.repositories.rates import RateRepository  # noqa: E402
from app.services.formatting import (  # noqa: E402
    format_cop,
    format_date_es,
    format_kwh,
    format_thousands,
)
from app.services.stats import StatsService  # noqa: E402

logger = logging.getLogger("energy_monitor.pdf")

# Paleta sobria (tema energético)
PRIMARY = colors.HexColor("#0f766e")      # verde azulado
PRIMARY_DARK = colors.HexColor("#134e4a")
ACCENT = colors.HexColor("#d97706")       # ámbar
TEXT = colors.HexColor("#1f2937")
MUTED = colors.HexColor("#6b7280")
LIGHT_BG = colors.HexColor("#f0fdfa")
WARN_BG = colors.HexColor("#fef3c7")
CHART_COLORS = ["#0f766e", "#d97706", "#7c3aed", "#dc2626", "#2563eb",
                "#059669", "#db2777", "#65a30d", "#9333ea", "#0ea5e9"]

PAGE_W, PAGE_H = A4
MARGIN = 2.0 * cm


def assets_file(name: str) -> str | None:
    """Ruta de un asset reemplazable, si existe."""
    path = os.path.join(settings.assets_dir, name)
    return path if os.path.isfile(path) else None


def logo_path() -> str | None:
    return assets_file("logo.png")


# ----------------------------------------------------------------------
# Registro de fuentes Unicode (tildes, ñ, etc.) con fallback robusto
# ----------------------------------------------------------------------
def _register_unicode_fonts() -> None:
    """Registra DejaVuSans (viene con matplotlib) para soporte completo
    de tildes/ñ; si no está disponible, Helvetica cubre Latin-1 básico."""
    candidates = []
    try:
        import matplotlib as mpl
        mpl_dir = os.path.join(os.path.dirname(mpl.__file__), "mpl-data", "fonts", "ttf")
        candidates.append(os.path.join(mpl_dir, "DejaVuSans.ttf"))
        candidates.append(os.path.join(mpl_dir, "DejaVuSans-Bold.ttf"))
    except Exception:  # noqa: BLE001
        pass
    try:
        if os.path.isfile(candidates[0]):
            pdfmetrics.registerFont(TTFont("DejaVu", candidates[0]))
        if len(candidates) > 1 and os.path.isfile(candidates[1]):
            pdfmetrics.registerFont(TTFont("DejaVu-Bold", candidates[1]))
    except Exception:  # noqa: BLE001
        logger.debug("No se pudieron registrar fuentes DejaVu; se usa Helvetica.")


_register_unicode_fonts()

BASE_FONT = "DejaVu" if "DejaVu" in pdfmetrics.getRegisteredFontNames() else "Helvetica"
BOLD_FONT = "DejaVu-Bold" if "DejaVu-Bold" in pdfmetrics.getRegisteredFontNames() else "Helvetica-Bold"


def _styles() -> dict:
    ss = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=ss["Title"], fontName=BOLD_FONT,
                                fontSize=20, textColor=PRIMARY_DARK, spaceAfter=2),
        "subtitle": ParagraphStyle("subtitle", parent=ss["Normal"], fontName=BASE_FONT,
                                   fontSize=11.5, textColor=MUTED, spaceAfter=10),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontName=BOLD_FONT,
                             fontSize=13, textColor=PRIMARY_DARK,
                             spaceBefore=14, spaceAfter=6),
        "body": ParagraphStyle("body", parent=ss["Normal"], fontName=BASE_FONT,
                               fontSize=9.5, textColor=TEXT, leading=13),
        "warn": ParagraphStyle("warn", parent=ss["Normal"], fontName=BASE_FONT,
                               fontSize=9.5, textColor=colors.HexColor("#92400e"), leading=13),
        "small": ParagraphStyle("small", parent=ss["Normal"], fontName=BASE_FONT,
                                fontSize=8, textColor=MUTED, leading=10),
    }


# ----------------------------------------------------------------------
# Gráficas matplotlib (PNG en memoria)
# ----------------------------------------------------------------------
def _style_axes(ax) -> None:
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color("#9ca3af")
    ax.spines["bottom"].set_color("#9ca3af")
    ax.tick_params(colors="#4b5563", labelsize=8)
    ax.grid(axis="y", color="#e5e7eb", linewidth=0.7)
    ax.set_axisbelow(True)


def _fig_to_png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def chart_daily_total(series: list[dict]) -> bytes | None:
    """Gráfica: consumo diario total (línea)."""
    if not series:
        return None
    dates = [dt.date.fromisoformat(p["date"]) for p in series]
    values = [p["total"] for p in series]
    fig, ax = plt.subplots(figsize=(9.2, 3.1), constrained_layout=True)
    ax.plot(dates, values, color=CHART_COLORS[0], linewidth=1.8, marker="o",
            markersize=2.5, markerfacecolor=CHART_COLORS[0])
    ax.fill_between(dates, values, color=CHART_COLORS[0], alpha=0.12)
    ax.set_ylabel("kWh", fontsize=9)
    ax.set_title("Consumo diario total", fontsize=11, color="#134e4a", loc="left")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%d/%m"))
    _style_axes(ax)
    return _fig_to_png(fig)


def chart_by_device(by_device: list[dict]) -> bytes | None:
    """Gráfica: consumo total por dispositivo en el periodo (barras)."""
    if not by_device:
        return None
    names = [d["device_name"] for d in by_device]
    values = [d["kwh"] for d in by_device]
    fig, ax = plt.subplots(figsize=(9.2, 3.1), constrained_layout=True)
    bars = ax.bar(names, values, color=CHART_COLORS[: len(names)], width=0.55)
    for bar, val in zip(bars, values):
        ax.annotate(format_thousands(val, 2), (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    ha="center", va="bottom", fontsize=8, color="#374151")
    ax.set_ylabel("kWh", fontsize=9)
    ax.set_title("Consumo total por dispositivo", fontsize=11, color="#134e4a", loc="left")
    ax.tick_params(axis="x", labelsize=8.5)
    _style_axes(ax)
    return _fig_to_png(fig)


def chart_daily_per_device(per_device: dict[str, list[dict]], names: dict[str, str]) -> bytes | None:
    """Gráfica: consumo diario por dispositivo (una serie por dispositivo)."""
    if not per_device:
        return None
    fig, ax = plt.subplots(figsize=(9.2, 3.4), constrained_layout=True)
    has_data = False
    for i, (dev_id, points) in enumerate(sorted(per_device.items(), key=lambda kv: kv[0])):
        if not points:
            continue
        has_data = True
        dates = [dt.date.fromisoformat(p["date"]) for p in points]
        values = [p["kwh"] for p in points]
        ax.plot(dates, values, linewidth=1.4, color=CHART_COLORS[i % len(CHART_COLORS)],
                label=names.get(dev_id, f"Dispositivo {dev_id}"))
    if not has_data:
        plt.close(fig)
        return None
    ax.set_ylabel("kWh", fontsize=9)
    ax.set_title("Consumo diario por dispositivo", fontsize=11, color="#134e4a", loc="left")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%d/%m"))
    ax.legend(fontsize=7.5, frameon=False, ncol=min(len(per_device), 3))
    _style_axes(ax)
    return _fig_to_png(fig)


# ----------------------------------------------------------------------
# Canvas con numeración "Página X de Y"
# ----------------------------------------------------------------------
class NumberedCanvas(pdfcanvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_states: list = []

    def showPage(self):
        self._saved_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_states)
        for state in self._saved_states:
            self.__dict__.update(state)
            self._draw_footer(total)
            super().showPage()
        super().save()

    def _draw_footer(self, total: int) -> None:
        page_num = self._pageNumber
        self.saveState()
        self.setStrokeColor(colors.HexColor("#d1d5db"))
        self.setLineWidth(0.6)
        self.line(MARGIN, 1.35 * cm, PAGE_W - MARGIN, 1.35 * cm)
        self.setFont(BASE_FONT, 7.5)
        self.setFillColor(MUTED)
        self.drawString(MARGIN, 1.0 * cm,
                        f"{settings.app_name} — Informe de consumo energético")
        generated = dt.datetime.now().strftime("%d/%m/%Y %H:%M")
        self.drawRightString(PAGE_W - MARGIN, 1.0 * cm,
                             f"Página {page_num} de {total} · Generado: {generated}")
        self.restoreState()


# ----------------------------------------------------------------------
# Servicio principal
# ----------------------------------------------------------------------
class PDFReportService:
    def __init__(self, db) -> None:
        self.db = db

    def generate(self, date_from: dt.date, date_to: dt.date, device_ids: list[int] | None) -> bytes:
        # device_ids None = todos los dispositivos
        if device_ids is None:
            devices = self.db.execute(select(Device).order_by(Device.name)).scalars().all()
            device_ids = [d.id for d in devices]
        if not device_ids:
            from app.services.errors import ValidationError
            raise ValidationError("No hay dispositivos para incluir en el informe.")

        stats = StatsService(self.db)
        summary = stats.period_summary(device_ids, date_from, date_to)
        per_device_series = stats.per_device_series(device_ids, date_from, date_to)
        rates_used = RateRepository(self.db).rates_for_period(date_from, date_to)
        device_names = {str(d["device_id"]): d["device_name"] for d in
                        (bd.model_dump() for bd in summary["by_device"])}

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=A4,
            leftMargin=MARGIN, rightMargin=MARGIN, topMargin=1.6 * cm, bottomMargin=1.8 * cm,
            title=f"{settings.app_name} — Informe de consumo energético",
            author=settings.app_name,
        )
        st = _styles()
        story: list = []

        # ---------- Encabezado ----------
        logo = logo_path()
        header_cells = []
        if logo:
            try:
                header_cells.append(Image(logo, width=1.4 * cm, height=1.4 * cm, kind="proportional"))
            except Exception:  # noqa: BLE001
                logger.warning("No se pudo cargar el logo del informe: %s", logo)
        header_cells.append(Paragraph("ENERGY MONITOR", st["title"]))
        block = Table([[header_cells]], colWidths=[PAGE_W - 2 * MARGIN])
        block.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(block)
        story.append(Paragraph("Informe de consumo energético", st["subtitle"]))
        meta = Table(
            [[Paragraph(f"<b>Periodo:</b> {format_date_es(date_from)} – {format_date_es(date_to)}", st["body"]),
              Paragraph(f"<b>Fecha de generación:</b> {dt.datetime.now().strftime('%d/%m/%Y %H:%M')}", st["body"])]],
            colWidths=[(PAGE_W - 2 * MARGIN) * 0.5, (PAGE_W - 2 * MARGIN) * 0.5],
        )
        meta.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(meta)
        story.append(self._divider())

        # ---------- Resumen general ----------
        story.append(Paragraph("Resumen general", st["h2"]))
        cost_text = format_cop(summary["total_cost"])
        if summary["cost_incomplete"]:
            cost_text += "  *"
        general_rows = [
            ["Consumo total", format_kwh(summary["total_kwh"])],
            ["Costo total calculable", cost_text],
            ["Promedio diario (días con datos)", format_kwh(summary["avg_daily_kwh"])],
            ["Número de dispositivos", str(summary["devices_count"])],
            ["Número de días del periodo", str(summary["days"])],
            ["Días con datos / sin datos",
             f"{summary['days_with_data']} / {summary['days_without_data']}"],
        ]
        story.append(self._table([["Indicador", "Valor"], *general_rows], col_widths=[9 * cm, 8 * cm],
                                 highlight_last=False))

        # ---------- Resumen por dispositivo ----------
        story.append(Paragraph("Resumen por dispositivo", st["h2"]))
        dev_rows = [["Dispositivo", "Consumo (kWh)", "Costo estimado"]]
        for d in summary["by_device"]:
            cost = format_cop(d.cost)
            if d.cost_incomplete:
                cost += "  *"
            dev_rows.append([d.device_name, format_thousands(d.kwh, 2), cost])
        dev_rows.append(["TOTAL", format_thousands(summary["total_kwh"], 2), cost_text])
        story.append(self._table(dev_rows, col_widths=[7.5 * cm, 4.5 * cm, 5 * cm],
                                 highlight_last=True))

        # ---------- Gráficas ----------
        chart1 = chart_daily_total([p.model_dump(mode="json") for p in summary["series"]])
        if chart1:
            story += self._chart_section(story, "Gráfica de consumo diario total", chart1)

        chart2 = chart_by_device([d.model_dump() for d in summary["by_device"]])
        if chart2:
            story += self._chart_section(story, "Gráfica de consumo por dispositivo", chart2)

        if len(device_ids) > 1:
            chart3 = chart_daily_per_device(per_device_series, device_names)
            if chart3:
                story += self._chart_section(story, "Gráfica de consumo diario por dispositivo", chart3)

        # ---------- Información de tarifas ----------
        story.append(Paragraph("Información de tarifas", st["h2"]))
        if rates_used:
            rate_rows = [["Vigencia", "Precio (COP/kWh)"]]
            for r in sorted(rates_used, key=lambda x: x.start_date):
                vigencia = (f"{format_date_es(r.start_date)} – "
                            f"{format_date_es(r.end_date) if r.end_date else 'vigente indefinida'}")
                rate_rows.append([vigencia, format_thousands(r.price_per_kwh, 2)])
            story.append(self._table(rate_rows, col_widths=[9 * cm, 8 * cm], highlight_last=False))
        else:
            story.append(Paragraph("No existen tarifas configuradas para este periodo.", st["body"]))

        # ---------- Advertencias ----------
        warnings: list[str] = []
        if summary["days_without_rate"] > 0:
            ranges = ", ".join(summary["missing_rate_ranges"])
            warnings.append(
                "ADVERTENCIA: Existen días sin tarifa configurada. "
                f"El costo de esos días no fue incluido ({ranges})."
            )
        if summary["days_without_data"] > 0:
            warnings.append(
                f"El periodo contiene {summary['days_without_data']} día(s) sin registros de consumo. "
                "No se asume consumo cero para los días sin registro."
            )
        if summary["cost_incomplete"]:
            warnings.append("(*) El costo de algunos dispositivos quedó parcialmente calculado "
                            "por faltar tarifa en parte de sus días con consumo.")
        if warnings:
            story.append(Paragraph("Advertencias", st["h2"]))
            warn_cell = "<br/>".join(f"• {w}" for w in warnings)
            warn_table = Table([[Paragraph(warn_cell, st["warn"])]],
                               colWidths=[PAGE_W - 2 * MARGIN])
            warn_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), WARN_BG),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#f59e0b")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(warn_table)

        doc.build(story, canvasmaker=NumberedCanvas)
        return buf.getvalue()

    # ------------------------------------------------------------------
    def _divider(self):
        t = Table([[""]], colWidths=[PAGE_W - 2 * MARGIN], rowHeights=[2])
        t.setStyle(TableStyle([
            ("LINEBELOW", (0, 0), (-1, -1), 1, PRIMARY),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        return t

    def _table(self, rows: list[list], col_widths: list, highlight_last: bool):
        data = [[Paragraph(f"<b>{c}</b>", _styles()["body"]) if i == 0 else Paragraph(str(c), _styles()["body"])
                 for c in row] for i, row in enumerate(rows)]
        t = Table(data, colWidths=col_widths, repeatRows=1)
        style = [
            ("FONTNAME", (0, 0), (-1, -1), BASE_FONT),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (-1, -1), TEXT),
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]
        if highlight_last:
            style += [("BACKGROUND", (0, -1), (-1, -1), PRIMARY_DARK),
                      ("TEXTCOLOR", (0, -1), (-1, -1), colors.white)]
        t.setStyle(TableStyle(style))
        return t

    def _chart_section(self, story: list, title: str, png: bytes) -> list:
        st = _styles()
        img = Image(io.BytesIO(png), width=PAGE_W - 2 * MARGIN, height=(PAGE_W - 2 * MARGIN) * 0.34,
                    kind="proportional")
        img.drawWidth = PAGE_W - 2 * MARGIN
        img.drawHeight = img.imageHeight * img.drawWidth / img.imageWidth
        return [Paragraph(title, st["h2"]), img, Spacer(1, 6)]
