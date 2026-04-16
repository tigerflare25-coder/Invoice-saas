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
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet

from .models import Invoice, InvoiceItem


# ===============================
# DASHBOARD
# ===============================

@login_required
def dashboard(request):
    request.user.check_premium_status()

    # Upload logo (premium only)
    if request.method == "POST" and request.FILES.get("logo"):
        if request.user.is_premium:
            request.user.logo = request.FILES["logo"]
            request.user.save()
        else:
            return redirect('upgrade')

    invoices = request.user.invoice_set.all().order_by('-created_at')

    # Auto mark overdue
    for inv in invoices:
        if inv.due_date and inv.due_date < date.today() and inv.status == "pending":
            inv.status = "overdue"
            inv.save()

    total = sum(inv.total_amount() for inv in invoices)

    return render(request, "invoices/dashboard.html", {
        "invoices": invoices,
        "total_amount": total,
        "invoice_count": invoices.count(),
    })


# ===============================
# CREATE INVOICE
# ===============================

@login_required
def create_invoice(request):
    if request.method == 'POST':
        client_name = request.POST.get('client_name', '').strip()
        template = request.POST.get('template', 'minimal')

        # Payment link
        payment_link = request.POST.get('payment_link', '').strip()
        if not payment_link:
            payment_link = request.user.payment_link

        payment_link = payment_link or None
        due_date = request.POST.get('due_date') or None

        # TAX (premium only)
        tax_val = 0
        tax_input = request.POST.get('tax_percentage', '').strip()

        if request.user.is_premium and tax_input:
            try:
                tax_val = max(float(tax_input), 0)
            except ValueError:
                tax_val = 0

        # Create invoice
        invoice = Invoice.objects.create(
            user=request.user,
            client_name=client_name or "Unnamed Client",
            tax_percentage=tax_val,
            template=template,
            payment_link=payment_link,
            due_date=due_date
        )

        # Items
        descriptions = request.POST.getlist('desc[]')
        quantities = request.POST.getlist('qty[]')
        prices = request.POST.getlist('price[]')

        for i in range(len(descriptions)):
            desc = descriptions[i].strip()
            if not desc:
                continue

            try:
                qty = max(int(quantities[i]), 1)
            except (ValueError, IndexError):
                qty = 1

            try:
                price = max(float(prices[i]), 0)
            except (ValueError, IndexError):
                price = 0

            InvoiceItem.objects.create(
                invoice=invoice,
                description=desc,
                quantity=qty,
                unit_price=price
            )

        return redirect('dashboard')

    return render(request, 'invoices/create.html')


# ===============================
# PDF HELPERS
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
        except Exception:
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

    # Payment link
    payment_link = invoice.payment_link or invoice.user.payment_link

    if payment_link:
        y -= 40
        p.setFillColor(colors.blue)

        p.setFillColor(colors.blue)
        p.drawString(40, y, "Pay Now:")
        p.linkURL(payment_link, (100, y - 2, 400, y + 12), relative=0)
        p.setFont("Helvetica", 9)
        p.drawString(100, y, payment_link[:50])
      



# Show actual URL (optional but better UX)


# Make link clickable


# Show text


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
# DOWNLOAD PDF
# ===============================

@login_required
def download_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id, user=request.user)
    items = invoice.items.all()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Invoice_{invoice.id}.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    if invoice.template == 'gst':
        render_gst(p, invoice, items, request, width, height)
    elif invoice.template == 'premium':
        render_premium(p, invoice, items, request, width, height)
    else:
        render_minimal(p, invoice, items, request, width, height)

    # Watermark for free users
    if not request.user.is_premium:
        p.setFont("Helvetica-Bold", 50)
        p.setFillColor(colors.lightgrey)
        p.drawCentredString(width / 2, height / 2, "FREE VERSION")

    # Footer
    p.setFont("Helvetica-Oblique", 8)
    p.setFillColor(colors.grey)
    p.drawCentredString(width / 2, 30, "Create your invoices at InvoiceFlow")

    p.showPage()
    p.save()

    return response
