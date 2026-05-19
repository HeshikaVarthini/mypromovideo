"""Professional PowerPoint report generation with charts."""

from __future__ import annotations

import io
from pathlib import Path

from pptx import Presentation
from app.chart_utils import render_bar_chart
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

from app.models import AnalysisReport, CompanyInsight, GapItem

# Brand palette
PRIMARY = RGBColor(0x1A, 0x36, 0x5D)      # deep navy
ACCENT = RGBColor(0x00, 0x96, 0xD6)       # bright blue
SECONDARY = RGBColor(0x64, 0x74, 0x8B)    # slate
LIGHT_BG = RGBColor(0xF1, 0xF5, 0xF9)    # light gray
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
CHART_COLORS = ["#1A365D", "#0096D6", "#38B2AC", "#ED8936", "#9F7AEA"]


def _add_bg(slide, color: RGBColor = LIGHT_BG) -> None:
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def _add_title_bar(slide, title: str, subtitle: str = "") -> None:
    bar = slide.shapes.add_shape(
        1, Inches(0), Inches(0), Inches(10), Inches(1.1)
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = PRIMARY
    bar.line.fill.background()

    box = slide.shapes.add_textbox(Inches(0.5), Inches(0.2), Inches(9), Inches(0.7))
    tf = box.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = WHITE

    if subtitle:
        sub = slide.shapes.add_textbox(
            Inches(0.5), Inches(0.75), Inches(9), Inches(0.35)
        )
        sp = sub.text_frame.paragraphs[0]
        sp.text = subtitle
        sp.font.size = Pt(12)
        sp.font.color.rgb = RGBColor(0xCB, 0xD5, 0xE1)


def _bullet_box(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    items: list[str],
    font_size: int = 14,
) -> None:
    box = slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(width), Inches(height)
    )
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = f"• {item}"
        p.font.size = Pt(font_size)
        p.font.color.rgb = RGBColor(0x33, 0x41, 0x55)
        p.space_after = Pt(8)


class PowerPointReportGenerator:
    def generate(self, report: AnalysisReport) -> bytes:
        prs = Presentation()
        prs.slide_width = Inches(10)
        prs.slide_height = Inches(7.5)

        self._slide_cover(prs, report)
        self._slide_executive_summary(prs, report)
        self._slide_channel_overview(prs, report)
        self._slide_subscriber_chart(prs, report)
        self._slide_content_performance(prs, report)
        self._slide_topics(prs, report)
        self._slide_posting_frequency(prs, report)
        self._slide_engagement(prs, report)
        self._slide_gap_analysis(prs, report)
        self._slide_recommendations(prs, report)
        self._slide_rankings(prs, report)

        buffer = io.BytesIO()
        prs.save(buffer)
        buffer.seek(0)
        return buffer.read()

    def _slide_cover(self, prs: Presentation, report: AnalysisReport) -> None:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        _add_bg(slide, PRIMARY)

        title_box = slide.shapes.add_textbox(
            Inches(0.8), Inches(2.2), Inches(8.4), Inches(1.5)
        )
        tp = title_box.text_frame.paragraphs[0]
        tp.text = "Video Competitor Intelligence Report"
        tp.font.size = Pt(36)
        tp.font.bold = True
        tp.font.color.rgb = WHITE
        tp.alignment = PP_ALIGN.CENTER

        names = [report.company] + report.competitors
        sub_box = slide.shapes.add_textbox(
            Inches(0.8), Inches(3.8), Inches(8.4), Inches(1.2)
        )
        sp = sub_box.text_frame.paragraphs[0]
        sp.text = " vs ".join(names)
        sp.font.size = Pt(20)
        sp.font.color.rgb = RGBColor(0x90, 0xCD, 0xF4)
        sp.alignment = PP_ALIGN.CENTER

        date_box = slide.shapes.add_textbox(
            Inches(0.8), Inches(5.5), Inches(8.4), Inches(0.5)
        )
        dp = date_box.text_frame.paragraphs[0]
        dp.text = report.generated_at.strftime("%B %d, %Y")
        dp.font.size = Pt(14)
        dp.font.color.rgb = RGBColor(0xCB, 0xD5, 0xE1)
        dp.alignment = PP_ALIGN.CENTER

    def _slide_executive_summary(self, prs: Presentation, report: AnalysisReport) -> None:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        _add_bg(slide)
        _add_title_bar(
            slide,
            "Executive Summary",
            f"Market leader: {report.leader}",
        )

        _bullet_box(
            slide, 0.6, 1.4, 8.8, 2.5,
            [report.executive_summary],
            font_size=13,
        )

        leader_box = slide.shapes.add_shape(
            1, Inches(0.6), Inches(4.2), Inches(8.8), Inches(2.2)
        )
        leader_box.fill.solid()
        leader_box.fill.fore_color.rgb = RGBColor(0xE0, 0xF2, 0xFE)
        leader_box.line.color.rgb = ACCENT

        lb = slide.shapes.add_textbox(
            Inches(0.9), Inches(4.5), Inches(8.2), Inches(1.8)
        )
        ltf = lb.text_frame
        ltf.word_wrap = True
        p1 = ltf.paragraphs[0]
        p1.text = f"🏆 {report.leader} leads this competitive set"
        p1.font.size = Pt(16)
        p1.font.bold = True
        p1.font.color.rgb = PRIMARY
        p2 = ltf.add_paragraph()
        p2.text = report.leader_reason
        p2.font.size = Pt(12)
        p2.font.color.rgb = SECONDARY

    def _slide_channel_overview(self, prs: Presentation, report: AnalysisReport) -> None:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        _add_bg(slide)
        _add_title_bar(slide, "Channel Overview Comparison")

        headers = ["Company", "Subscribers", "Total Videos", "Channel Views", "Uploads/Mo"]
        rows = []
        for ins in report.insights:
            rows.append([
                ins.company_name[:20],
                f"{ins.subscribers:,}",
                f"{ins.total_videos:,}",
                f"{ins.total_views:,}",
                f"{ins.uploads_per_month:.1f}",
            ])

        self._add_table(slide, 0.5, 1.5, headers, rows)

    def _slide_subscriber_chart(self, prs: Presentation, report: AnalysisReport) -> None:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        _add_bg(slide)
        _add_title_bar(slide, "Audience Reach Comparison", "Subscriber counts")

        m = report.comparative_metrics
        chart_path = render_bar_chart(
            m["companies"],
            [float(s) for s in m["subscribers"]],
            "Subscriber Count by Company",
            "Subscribers",
        )
        slide.shapes.add_picture(chart_path, Inches(1), Inches(1.4), width=Inches(8))
        Path(chart_path).unlink(missing_ok=True)

    def _slide_content_performance(self, prs: Presentation, report: AnalysisReport) -> None:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        _add_bg(slide)
        _add_title_bar(slide, "Content Performance", "Top videos by views")

        col_width = 4.2
        for idx, ins in enumerate(report.insights[:3]):
            left = 0.4 + (idx % 2) * 4.8
            top = 1.3 + (idx // 2) * 2.8
            if idx >= 2:
                break
            box = slide.shapes.add_textbox(
                Inches(left), Inches(top), Inches(col_width), Inches(2.5)
            )
            tf = box.text_frame
            tf.word_wrap = True
            h = tf.paragraphs[0]
            h.text = ins.company_name
            h.font.bold = True
            h.font.size = Pt(14)
            h.font.color.rgb = PRIMARY
            for v in ins.top_videos[:3]:
                p = tf.add_paragraph()
                title = v.title[:45] + ("…" if len(v.title) > 45 else "")
                p.text = f"• {title} — {v.views:,} views ({v.engagement_rate}% eng.)"
                p.font.size = Pt(10)
                p.font.color.rgb = SECONDARY

        if len(report.insights) > 2:
            note = slide.shapes.add_textbox(
                Inches(0.4), Inches(6.5), Inches(9), Inches(0.5)
            )
            np = note.text_frame.paragraphs[0]
            others = ", ".join(i.company_name for i in report.insights[2:])
            np.text = f"See web report for top videos from: {others}"
            np.font.size = Pt(10)
            np.font.italic = True
            np.font.color.rgb = SECONDARY

    def _slide_topics(self, prs: Presentation, report: AnalysisReport) -> None:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        _add_bg(slide)
        _add_title_bar(slide, "Content Topics & Themes")

        for idx, ins in enumerate(report.insights):
            col = idx % 3
            row = idx // 3
            left = 0.4 + col * 3.2
            top = 1.4 + row * 2.6
            box = slide.shapes.add_textbox(
                Inches(left), Inches(top), Inches(3), Inches(2.4)
            )
            tf = box.text_frame
            tf.word_wrap = True
            h = tf.paragraphs[0]
            h.text = ins.company_name
            h.font.bold = True
            h.font.size = Pt(13)
            h.font.color.rgb = PRIMARY
            topics = ins.top_topics[:5] or ["No recurring themes detected"]
            for t in topics:
                p = tf.add_paragraph()
                p.text = f"• {t}"
                p.font.size = Pt(11)

    def _slide_posting_frequency(self, prs: Presentation, report: AnalysisReport) -> None:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        _add_bg(slide)
        _add_title_bar(slide, "Posting Frequency & Consistency")

        m = report.comparative_metrics
        chart_path = render_bar_chart(
            m["companies"],
            m["uploads_per_month"],
            "Estimated Uploads per Month",
            "Videos / Month",
        )
        slide.shapes.add_picture(chart_path, Inches(0.5), Inches(1.3), width=Inches(5.5))
        Path(chart_path).unlink(missing_ok=True)

        items = []
        for ins in report.insights:
            items.append(
                f"{ins.company_name}: {ins.uploads_per_month:.1f}/mo, "
                f"consistency {ins.posting_consistency_score:.0f}/100"
            )
        _bullet_box(slide, 6.2, 1.5, 3.5, 4.5, items, font_size=11)

    def _slide_engagement(self, prs: Presentation, report: AnalysisReport) -> None:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        _add_bg(slide)
        _add_title_bar(slide, "Engagement Analysis")

        m = report.comparative_metrics
        chart_path = render_bar_chart(
            m["companies"],
            m["avg_engagement"],
            "Average Engagement Rate (%)",
            "Engagement %",
            horizontal=True,
        )
        slide.shapes.add_picture(chart_path, Inches(0.5), Inches(1.3), width=Inches(5.5))
        Path(chart_path).unlink(missing_ok=True)

        headers = ["Company", "Avg Views", "Avg Likes", "Avg Comments", "Eng. Rate"]
        rows = []
        for ins in report.insights:
            rows.append([
                ins.company_name[:18],
                f"{ins.avg_views_per_video:,.0f}",
                f"{ins.avg_likes_per_video:.0f}",
                f"{ins.avg_comments_per_video:.0f}",
                f"{ins.avg_engagement_rate:.2f}%",
            ])
        self._add_table(slide, 5.8, 1.5, headers, rows, col_widths=[1.2, 0.9, 0.8, 0.9, 0.8])

    def _slide_gap_analysis(self, prs: Presentation, report: AnalysisReport) -> None:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        _add_bg(slide)
        _add_title_bar(slide, "Gap Analysis", "Opportunities your brand can capture")

        items = []
        for gap in report.gap_analysis[:6]:
            items.append(
                f"{gap.topic_or_format}: covered by {', '.join(gap.covered_by[:3])}. "
                f"{gap.opportunity[:120]}…"
                if len(gap.opportunity) > 120
                else f"{gap.topic_or_format}: covered by {', '.join(gap.covered_by[:3])}. {gap.opportunity}"
            )
        if not items:
            items = [
                "No significant content gaps detected — focus on execution quality and frequency."
            ]
        _bullet_box(slide, 0.6, 1.4, 8.8, 5.5, items, font_size=12)

    def _slide_recommendations(self, prs: Presentation, report: AnalysisReport) -> None:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        _add_bg(slide)
        _add_title_bar(
            slide,
            "Video Marketing Recommendations",
            f"Tailored for {report.company}",
        )
        _bullet_box(slide, 0.6, 1.4, 8.8, 5.5, report.recommendations, font_size=13)

    def _slide_rankings(self, prs: Presentation, report: AnalysisReport) -> None:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        _add_bg(slide, PRIMARY)
        _add_title_bar(slide, "Competitive Scorecard", "Overall video marketing ranking")

        headers = ["Rank", "Company", "Overall", "Audience", "Engagement", "Consistency", "Volume"]
        rows = []
        for r in report.rankings:
            rows.append([
                f"#{r.rank}",
                r.company_name[:22],
                f"{r.overall_score:.0f}",
                f"{r.subscriber_score:.0f}",
                f"{r.engagement_score:.0f}",
                f"{r.consistency_score:.0f}",
                f"{r.content_volume_score:.0f}",
            ])
        self._add_table(
            slide, 0.8, 1.6, headers, rows,
            header_color=ACCENT, light=True,
        )

        foot = slide.shapes.add_textbox(Inches(0.8), Inches(6.2), Inches(8.4), Inches(0.6))
        fp = foot.text_frame.paragraphs[0]
        fp.text = "Scores are composite (0–100) based on subscribers, engagement, consistency, and content volume."
        fp.font.size = Pt(10)
        fp.font.color.rgb = RGBColor(0xCB, 0xD5, 0xE1)

    def _add_table(
        self,
        slide,
        left: float,
        top: float,
        headers: list[str],
        rows: list[list[str]],
        col_widths: list[float] | None = None,
        header_color: RGBColor = PRIMARY,
        light: bool = False,
    ) -> None:
        n_rows = len(rows) + 1
        n_cols = len(headers)
        width = sum(col_widths) if col_widths else 9.0
        table_shape = slide.shapes.add_table(
            n_rows, n_cols,
            Inches(left), Inches(top),
            Inches(width), Inches(0.35 * n_rows),
        )
        table = table_shape.table

        if col_widths:
            for i, w in enumerate(col_widths):
                table.columns[i].width = Inches(w)

        for j, h in enumerate(headers):
            cell = table.cell(0, j)
            cell.text = h
            cell.fill.solid()
            cell.fill.fore_color.rgb = header_color
            p = cell.text_frame.paragraphs[0]
            p.font.bold = True
            p.font.size = Pt(10)
            p.font.color.rgb = WHITE
            p.alignment = PP_ALIGN.CENTER

        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                cell = table.cell(i + 1, j)
                cell.text = val
                if light and i == 0:
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = RGBColor(0x2B, 0x6C, 0xB0)
                elif i % 2 == 0:
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = RGBColor(0xF8, 0xFA, 0xFC)
                p = cell.text_frame.paragraphs[0]
                p.font.size = Pt(10)
                p.font.color.rgb = WHITE if (light and i == 0) else RGBColor(0x33, 0x41, 0x55)
                p.alignment = PP_ALIGN.CENTER
