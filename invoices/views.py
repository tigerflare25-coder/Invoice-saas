import requests
from io import BytesIO
from decimal import Decimal
from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

from .models import Invoice, InvoiceItem


# ===============================
# DASHBOARD
# ===============================
@login_required
def dashboard(request):
    request.user.check_premium_status()

    if request.method == "POST" and request.FILES.get("logo"):
        if request.user.is_premium:
            request.user.logo = request.FILES["logo"]
            request.user.save()
        else:
            return redirect('upgrade')

    invoices = request.user.invoice_set.all().order_by('-created_at')

    # Auto update overdue
    for inv in invoices:
        if inv.due_date and inv.due_date < date.today() and inv.status == "pending":
            inv.status = "overdue"
            inv.save()

    total = sum(inv.total_amount() for inv in invoices)

    context = {
        "invoices": invoices,
        "total_amount": total,
        "invoice_count": invoices.count(),
    }
    return render(request, "invoices/dashboard.html", context)


# ===============================
# CREATE INVOICE
# ===============================
@login_required
def create_invoice(request):
    if request.method == 'POST':

        tax_input = request.POST.get('tax_percentage', '0')
        tax_val = float(tax_input) if request.user.is_premium else 0

        template = request.POST.get('template', 'minimal')
        payment_link = request.POST.get('payment_link')

        invoice = Invoice.objects.create(
            user=request.user,
            client_name=request.POST.get('client_name'),
            tax_percentage=tax_val,
            template=template,
            payment_link=payment_link
        )

        descriptions = request.POST.getlist('desc[]')
        quantities = request.POST.getlist('qty[]')
        prices = request.POST.getlist('price[]')

        for i in range(len(descriptions)):
            if descriptions[i].strip():
                InvoiceItem.objects.create(
                    invoice=invoice,
                    description=descriptions[i],
                    quantity=int(quantities[i] or 1),
                    unit_price=float(prices[i] or 0)
                )

        return redirect('dashboard')

    return render(request, 'invoices/create.html')


# ===============================
# PDF TEMPLATE HELPERS
# ===============================

def draw_header(p, request, width, height):
    if request.user.is_premium:
        p.setFillColor(colors.HexColor("#E6FFFA"))
        p.rect(0, height - 120, width, 120, fill=1, stroke=0)

    p.setFillColor(colors.black)

    if request.user.is_premium and request.user.logo:
        try:
            res = requests.get(request.user.logo.url)
            img = ImageReader(BytesIO(res.content))
            p.drawImage(img, 40, height - 80, width=80, height=40)
        except:
            p.setFont("Helvetica-Bold", 18)
            p.drawString(40, height - 70, "INVOICEFLOW")
    else:
        p.setFont("Helvetica-Bold", 18)
        p.drawString(40, height - 70, "INVOICEFLOW")


def draw_items(p, items, width, height):
    y = height - 240

    p.setFillColor(colors.HexColor("#F3F4F6"))
    p.rect(40, y, width - 80, 25, fill=1)

    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, y + 7, "Description")
    p.drawString(320, y + 7, "Qty")
    p.drawString(390, y + 7, "Price")
    p.drawRightString(width - 50, y + 7, "Total")

    y -= 25
    subtotal = Decimal('0.00')

    for item in items:
        p.drawString(50, y, item.description)
        p.drawString(320, y, str(item.quantity))
        p.drawString(390, y, f"{item.unit_price}")

        total = item.total_price()
        p.drawRightString(width - 50, y, f"{total:.2f}")

        subtotal += Decimal(total)
        y -= 20

    return subtotal, y


# ===============================
# TEMPLATE RENDERERS
# ===============================

def render_minimal(p, invoice, items, request, width, height):
    draw_header(p, request, width, height)

    p.setFont("Helvetica-Bold", 24)
    p.drawRightString(width - 40, height - 70, "INVOICE")

    subtotal, y = draw_items(p, items, width, height)

    draw_summary(p, invoice, subtotal, y, width)


def render_gst(p, invoice, items, request, width, height):
    draw_header(p, request, width, height)

    p.setFont("Helvetica-Bold", 20)
    p.drawString(40, height - 100, "GST INVOICE")
    p.drawString(40, height - 115, "GSTIN: XXXXXXXX")

    subtotal, y = draw_items(p, items, width, height)

    draw_summary(p, invoice, subtotal, y, width)


def render_premium(p, invoice, items, request, width, height):
    p.setFillColor(colors.HexColor("#111827"))
    p.rect(0, height - 120, width, 120, fill=1)

    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 20)
    p.drawString(40, height - 80, "INVOICEFLOW")

    subtotal, y = draw_items(p, items, width, height)

    draw_summary(p, invoice, subtotal, y, width)


# ===============================
# SUMMARY + PAYMENT
# ===============================

def draw_summary(p, invoice, subtotal, y, width):
    y -= 20

    p.setFont("Helvetica", 10)
    p.drawString(350, y, "Subtotal:")
    p.drawRightString(width - 50, y, f"INR {subtotal:.2f}")

    total = subtotal

    if invoice.tax_percentage:
        tax = (subtotal * Decimal(str(invoice.tax_percentage))) / 100
        total += tax
        y -= 20
        p.drawString(350, y, f"Tax ({invoice.tax_percentage}%):")
        p.drawRightString(width - 50, y, f"INR {tax:.2f}")

    y -= 30
    p.setFont("Helvetica-Bold", 14)
    p.drawString(350, y, "TOTAL:")
    p.drawRightString(width - 50, y, f"INR {total:.2f}")

    # 🔥 PAYMENT LINK
    if invoice.payment_link:
        y -= 40
        p.setFillColor(colors.blue)
        p.drawString(40, y, f"Pay Now: {invoice.payment_link}")


# ===============================
# DOWNLOAD
# ===============================

@login_required
def download_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id, user=request.user)
    items = invoice.items.all()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Invoice_{invoice.id}.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # 🔥 TEMPLATE SWITCH
    if invoice.template == 'gst':
        render_gst(p, invoice, items, request, width, height)

    elif invoice.template == 'premium':
        render_premium(p, invoice, items, request, width, height)

    else:
        render_minimal(p, invoice, items, request, width, height)

    # WATERMARK
    if not request.user.is_premium:
        p.setFont("Helvetica-Bold", 50)
        p.setFillColor(colors.lightgrey)
        p.drawCentredString(width / 2, height / 2, "FREE VERSION")

    # 🔥 VIRAL FOOTER
    p.setFont("Helvetica-Oblique", 8)
    p.setFillColor(colors.grey)
    p.drawCentredString(width / 2, 30, "Create your invoices at InvoiceFlow")

    p.showPage()
    p.save()
    return response
