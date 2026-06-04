"""URL configuration for config project."""
from django import forms as django_forms
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError

from analyzer.forms import SimpleSignupForm
from analyzer.models import AnalysisSession, LibraryPaper


class EmailLoginForm(django_forms.Form):
    """A simple login form that takes email + password."""
    email = django_forms.EmailField(
        widget=django_forms.EmailInput(attrs={
            'placeholder': 'yourname@gmail.com',
            'autocomplete': 'email',
        })
    )
    password = django_forms.CharField(
        strip=False,
        widget=django_forms.PasswordInput(attrs={'placeholder': 'Enter your password'}),
    )

    def clean(self):
        cleaned = super().clean()
        email    = cleaned.get('email', '').strip().lower()
        password = cleaned.get('password', '')
        if email and password:
            # username IS the email in this app
            user = authenticate(username=email, password=password)
            if user is None:
                raise django_forms.ValidationError(
                    'Invalid email or password. Please try again.'
                )
            cleaned['user'] = user
        return cleaned

    def get_user(self):
        return self.cleaned_data.get('user')


# ─── Views ───────────────────────────────────────────

def index_view(request):
    """Landing page — redirect to dashboard if already logged in."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, "index.html")


def login_view(request):
    """Login page — authenticates using email address as username."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = EmailLoginForm()
    if request.method == 'POST':
        form = EmailLoginForm(data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('dashboard')
    return render(request, "login.html", {"form": form})


def signup_view(request):
    """Signup page using SimpleSignupForm."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = SimpleSignupForm()
    if request.method == 'POST':
        form = SimpleSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    return render(request, "signup.html", {"form": form})


def logout_view(request):
    """Logout and redirect to landing page."""
    logout(request)
    return redirect('index')


@login_required(login_url='/login/')
@ensure_csrf_cookie
def dashboard_view(request):
    """Main dashboard — paper selection + analysis."""
    return render(request, "dashboard.html")


@login_required(login_url='/login/')
def papers_view(request):
    """Paper library browse page."""
    return render(request, "papers.html")


@login_required(login_url='/login/')
def history_view(request):
    """User's past analysis history."""
    sessions = AnalysisSession.objects.filter(
        user=request.user
    ).select_related('result').order_by('-created_at')[:30]
    return render(request, "history.html", {'sessions': sessions})


@login_required(login_url='/login/')
def session_result_view(request, session_id):
    """View saved results of a completed analysis session."""
    from analyzer.models import AnalysisResult
    import json
    session = get_object_or_404(AnalysisSession, id=session_id, user=request.user)
    result = None
    if session.status == 'completed':
        result = AnalysisResult.objects.filter(session=session).first()
    return render(request, 'session_result.html', {
        'session': session,
        'result_json': json.dumps({
            'stage_2_insights': result.stage_2_deduplicated_json if result else {},
            'stage_3_predictive_dashboard': result.stage_3_dl_insights_json if result else {},
        })
    })


@login_required(login_url='/login/')
def print_result_view(request, session_id):
    """Renders a print-optimised page for the analysis result (browser prints to PDF)."""
    from analyzer.models import AnalysisResult
    import json
    session = get_object_or_404(AnalysisSession, id=session_id, user=request.user)
    result = None
    if session.status == 'completed':
        result = AnalysisResult.objects.filter(session=session).first()
    return render(request, 'print_result.html', {
        'session': session,
        'result_json': json.dumps({
            'stage_2_insights': result.stage_2_deduplicated_json if result else {},
            'stage_3_predictive_dashboard': result.stage_3_dl_insights_json if result else {},
        })
    })


@login_required(login_url='/login/')
def download_paper_view(request, paper_id):
    """Serves a LibraryPaper file as a direct download."""
    import mimetypes
    from django.http import FileResponse, Http404
    paper = get_object_or_404(LibraryPaper, id=paper_id)
    file_path = paper.pdf_file.path
    if not os.path.exists(file_path):
        raise Http404("File not found.")
    mime_type, _ = mimetypes.guess_type(file_path)
    mime_type = mime_type or 'application/octet-stream'
    filename = paper.pdf_file.name.split('/')[-1]
    response = FileResponse(open(file_path, 'rb'), content_type=mime_type)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required(login_url='/login/')
def download_result_pdf_view(request, session_id):
    """Generates and serves the analysis result as a downloadable PDF."""
    import io
    from django.http import HttpResponse
    from analyzer.models import AnalysisResult
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # ── Register a Hindi-capable font (Devanagari support) ──
    HINDI_FONT = 'Helvetica'
    HINDI_FONT_BOLD = 'Helvetica-Bold'
    _font_candidates = [
        (r'C:\Windows\Fonts\NirmalaUI.ttf',  r'C:\Windows\Fonts\NirmalaUIBold.ttf',  'NirmalaUI'),
        (r'C:\Windows\Fonts\NirmalaS.ttf',   r'C:\Windows\Fonts\NirmalaSBold.ttf',   'NirmalaS'),
        (r'C:\Windows\Fonts\mangal.ttf',     r'C:\Windows\Fonts\mangalb.ttf',        'Mangal'),
        (r'C:\Windows\Fonts\arial.ttf',      r'C:\Windows\Fonts\arialbd.ttf',        'Arial'),
    ]
    for reg_path, bold_path, fname in _font_candidates:
        if os.path.exists(reg_path):
            pdfmetrics.registerFont(TTFont(fname, reg_path))
            if os.path.exists(bold_path):
                pdfmetrics.registerFont(TTFont(fname + '-Bold', bold_path))
                HINDI_FONT_BOLD = fname + '-Bold'
            else:
                HINDI_FONT_BOLD = fname
            HINDI_FONT = fname
            break

    session = get_object_or_404(AnalysisSession, id=session_id, user=request.user)
    if session.status != 'completed':
        from django.http import HttpResponseBadRequest
        return HttpResponseBadRequest("Analysis not completed yet.")

    result = AnalysisResult.objects.filter(session=session).first()
    if not result:
        from django.http import HttpResponseBadRequest
        return HttpResponseBadRequest("No result found for this session.")

    s2 = result.stage_2_deduplicated_json or {}
    s3 = result.stage_3_dl_insights_json or {}
    repeated   = s2.get('repeated_questions', [])
    predicted  = s2.get('predicted_important_questions', [])
    strategy   = s3.get('chapter_wise_strategy', [])
    advice     = s3.get('final_student_advice', '')
    pattern    = s3.get('pattern_analysis', {})
    difficulty = s3.get('difficulty_breakdown', {})

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    BLUE   = colors.HexColor('#1e3a8a')
    LBLUE  = colors.HexColor('#3b82f6')
    ORANGE = colors.HexColor('#f59e0b')
    GREEN  = colors.HexColor('#16a34a')
    GRAY   = colors.HexColor('#64748b')
    LIGHT  = colors.HexColor('#f1f5f9')

    title_style = ParagraphStyle('TitleH', parent=styles['Title'],
        fontSize=22, textColor=BLUE, spaceAfter=4, fontName=HINDI_FONT_BOLD)
    h2_style = ParagraphStyle('H2H', parent=styles['Heading2'],
        fontSize=14, textColor=BLUE, spaceBefore=18, spaceAfter=6, fontName=HINDI_FONT_BOLD)
    h3_style = ParagraphStyle('H3H', parent=styles['Heading3'],
        fontSize=11, textColor=LBLUE, spaceBefore=10, spaceAfter=4, fontName=HINDI_FONT_BOLD)
    body_style = ParagraphStyle('BodyH', parent=styles['Normal'],
        fontSize=10, textColor=colors.HexColor('#0f172a'), leading=18, spaceAfter=4, fontName=HINDI_FONT)
    muted_style = ParagraphStyle('MutedH', parent=styles['Normal'],
        fontSize=9, textColor=GRAY, leading=15, fontName=HINDI_FONT)
    tag_style = ParagraphStyle('TagH', parent=styles['Normal'],
        fontSize=9, textColor=colors.HexColor('#1e40af'), leading=13, fontName=HINDI_FONT)

    story = []

    # ── Header ──
    story.append(Paragraph(f"MP Board Exam Analysis Report", title_style))
    story.append(Paragraph(
        f"Subject: <b>{session.subject}</b>  |  Class: <b>{session.student_class}</b>  |  "
        f"Date: <b>{session.created_at.strftime('%d %b %Y')}</b>",
        muted_style
    ))
    story.append(HRFlowable(width='100%', thickness=2, color=LBLUE, spaceAfter=16))

    # ── Stats Summary ──
    stats_data = [
        ['Predicted Questions', 'Repeated Questions', 'Chapters Covered'],
        [str(len(predicted)),   str(len(repeated)),   str(len(strategy))],
    ]
    stats_table = Table(stats_data, colWidths=[5.5*cm, 5.5*cm, 5.5*cm])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BLUE),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('FONTNAME',   (0,0), (-1,0), HINDI_FONT_BOLD),
        ('FONTSIZE',   (0,0), (-1,0), 10),
        ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
        ('BACKGROUND', (0,1), (-1,1), LIGHT),
        ('FONTNAME',   (0,1), (-1,1), HINDI_FONT_BOLD),
        ('FONTSIZE',   (0,1), (-1,1), 20),
        ('TEXTCOLOR',  (0,1), (0,1), ORANGE),
        ('TEXTCOLOR',  (1,1), (1,1), GREEN),
        ('TEXTCOLOR',  (2,1), (2,1), LBLUE),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [None, None]),
        ('BOX',        (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
        ('INNERGRID',  (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING',  (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(stats_table)
    story.append(Spacer(1, 18))

    # ── Predicted Questions ──
    story.append(Paragraph("Predicted Important Questions", h2_style))
    story.append(HRFlowable(width='100%', thickness=1, color=ORANGE, spaceAfter=8))
    for i, q in enumerate(predicted, 1):
        story.append(Paragraph(f"{i}. {q.get('question', '')}", body_style))
        meta = []
        if q.get('marks'):        meta.append(f"Marks: {q['marks']}")
        if q.get('topic'):        meta.append(f"Topic: {q['topic']}")
        if q.get('question_type'): meta.append(f"Type: {q['question_type']}")
        if q.get('reason'):       meta.append(f"Reason: {q['reason']}")
        if meta:
            story.append(Paragraph('  |  '.join(meta), tag_style))
        story.append(Spacer(1, 6))

    # ── Repeated Questions ──
    story.append(Spacer(1, 8))
    story.append(Paragraph("Repeated Questions", h2_style))
    story.append(HRFlowable(width='100%', thickness=1, color=GREEN, spaceAfter=8))
    for i, q in enumerate(repeated, 1):
        story.append(Paragraph(f"{i}. {q.get('question', '')}", body_style))
        years_str = ', '.join(q.get('years', [])) if isinstance(q.get('years'), list) else str(q.get('years', ''))
        meta = []
        if q.get('marks'):        meta.append(f"Marks: {q['marks']}")
        if q.get('topic'):        meta.append(f"Topic: {q['topic']}")
        if q.get('frequency'):    meta.append(f"Repeated: {q['frequency']}x")
        if years_str:             meta.append(f"Years: {years_str}")
        if meta:
            story.append(Paragraph('  |  '.join(meta), tag_style))
        story.append(Spacer(1, 6))

    # ── Chapter Strategy ──
    if strategy:
        story.append(Spacer(1, 8))
        story.append(Paragraph("Chapter-wise Study Strategy", h2_style))
        story.append(HRFlowable(width='100%', thickness=1, color=LBLUE, spaceAfter=8))
        ch_data = [['Chapter', 'Priority', 'Study Tip']]
        for ch in strategy:
            ch_data.append([
                Paragraph(ch.get('chapter_name', ch.get('chapter', '')), muted_style),
                ch.get('priority_level', ''),
                Paragraph(ch.get('study_tip', ''), muted_style),
            ])
        ch_table = Table(ch_data, colWidths=[5*cm, 2.5*cm, 9.5*cm])
        ch_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), BLUE),
            ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
            ('FONTNAME',   (0,0), (-1,0), HINDI_FONT_BOLD),
            ('FONTSIZE',   (0,0), (-1,0), 9),
            ('ALIGN',      (1,0), (1,-1), 'CENTER'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LIGHT]),
            ('BOX',        (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
            ('INNERGRID',  (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING',  (0,0), (-1,-1), 7),
            ('BOTTOMPADDING', (0,0), (-1,-1), 7),
            ('LEFTPADDING',  (0,0), (-1,-1), 8),
        ]))
        story.append(ch_table)

    # ── Final Advice ──
    if advice:
        story.append(Spacer(1, 16))
        story.append(Paragraph("AI Study Advice", h2_style))
        story.append(Paragraph(advice, body_style))

    doc.build(story)
    buffer.seek(0)

    safe_subject = session.subject.replace(' ', '_')
    filename = f"MP_Board_{safe_subject}_{session.student_class}_Analysis.pdf"
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


from analyzer.views import admin_bulk_upload_view, delete_paper_view, delete_papers_bulk_view
from django.shortcuts import get_object_or_404
import os

urlpatterns = [
    path('',          index_view,     name='index'),
    path('login/',    login_view,     name='login'),
    path('signup/',   signup_view,    name='signup'),
    path('logout/',   logout_view,    name='logout'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('papers/',   papers_view,    name='papers'),
    path('history/',  history_view,   name='history'),
    path('results/<uuid:session_id>/', session_result_view, name='session_result'),
    path('results/<uuid:session_id>/print/', print_result_view, name='print_result'),
    path('results/<uuid:session_id>/download-pdf/', download_result_pdf_view, name='download_result_pdf'),
    path('papers/download/<int:paper_id>/', download_paper_view, name='download_paper'),
    
    # Custom Admin Dashboard
    path('admin/',    admin_bulk_upload_view, name='admin_home'),
    path('admin/delete/<int:paper_id>/', delete_paper_view, name='delete_paper'),
    path('admin/delete-bulk/', delete_papers_bulk_view, name='delete_papers_bulk'),
    
    path('api/',      include('analyzer.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
