import requests
from io import BytesIO
from decimal import Decimal
from django.utils import timezone
from accounts import models

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Sum, F
from reportlab.lib.utils import ImageReader

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from django.contrib.auth import get_user_model


from .models import Invoice, InvoiceItem

@login_required
def dashboard(request):

    request.user.check_premium_status()
    # Handle Logo Upload
    if request.method == "POST" and request.FILES.get("logo"):
        if request.user.is_premium:
            request.user.logo = request.FILES["logo"]
            request.user.save()
            return redirect('dashboard')
        else:
            return redirect('upgrade')

    # Fetch User's Invoices
    invoices = request.user.invoice_set.all().order_by('-created_at')

    # Calculate total invoiced amount using your model's total_amount method
    total_invoiced = sum(invoice.total_amount() for invoice in invoices) if invoices else 0
    
    context = {
        "invoices": invoices,
        "total_amount": total_invoiced,
        "invoice_count": invoices.count(),
    }
    return render(request, "invoices/dashboard.html", context)

@login_required
def create_invoice(request):
    if request.method == 'POST':
        # Get tax safely
        tax_input = request.POST.get('tax_percentage', '0')
        tax_val = float(tax_input) if tax_input and request.user.is_premium else 0

        # 1. Create the Invoice
        invoice = Invoice.objects.create(
            user=request.user,
            client_name=request.POST.get('client_name'),
            tax_percentage=tax_val
        )

        # 2. Get the lists
        descriptions = request.POST.getlist('desc[]')
        quantities = request.POST.getlist('qty[]')
        prices = request.POST.getlist('price[]')

        # 3. Save each item safely
        for i in range(len(descriptions)):
            desc = descriptions[i].strip()
            if desc:
                qty = int(quantities[i]) if quantities[i] else 1
                price = float(prices[i]) if prices[i] else 0.0

                InvoiceItem.objects.create(
                    invoice=invoice,
                    description=desc,
                    quantity=qty,
                    unit_price=price
                )
        
        return redirect('dashboard')

    return render(request, 'invoices/create.html')

@login_required
def download_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id, user=request.user)
    items = invoice.items.all()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Invoice_{invoice.id}.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # --- 1. PREMIUM HEADER ---
    if request.user.is_premium:
        p.setFillColor(colors.HexColor("#E6FFFA"))
        p.rect(0, height - 120, width, 120, fill=1, stroke=0)
    
    p.setFillColor(colors.black)
    
    # --- 2. LOGO (FIXED INDENTATION) ---
    if request.user.is_premium and request.user.logo:
        try:
            logo_url = request.user.logo.url
            res = requests.get(logo_url)
            logo_data = BytesIO(res.content)
        
        # WRAP THE DATA HERE:
            img = ImageReader(logo_data) 
        
        # Draw using 'img' instead of 'logo_data'
            p.drawImage(img, 40, height - 80, width=80, height=40, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            print(f"Cloudinary Logo Error: {e}")
            p.setFont("Helvetica-Bold", 18)
            p.drawString(40, height - 70, "INVOICEFLOW")
    else:
        # Fallback Brand Name
        p.setFont("Helvetica-Bold", 18)
        p.drawString(40, height - 70, "INVOICEFLOW")

    # --- 3. INVOICE TITLE & DETAILS ---
    p.setFont("Helvetica-Bold", 24)
    p.drawRightString(width - 40, height - 70, "INVOICE")
    
    p.setFont("Helvetica", 10)
    p.drawRightString(width - 40, height - 85, f"Invoice #: INV-{invoice.id:04d}")
    p.drawRightString(width - 40, height - 100, f"Date: {invoice.created_at.strftime('%d %b, %Y')}")

    # --- 4. BILLING SECTION ---
    p.setFont("Helvetica-Bold", 11)
    p.drawString(40, height - 160, "BILL FROM:")
    p.drawString(width/2 + 20, height - 160, "BILL TO:")

    p.setFont("Helvetica", 10)
    p.drawString(40, height - 175, f"{request.user.get_full_name() or request.user.username}")
    p.drawString(40, height - 188, f"{request.user.email}")
    p.drawString(width/2 + 20, height - 175, f"{invoice.client_name}")

    # --- 5. TABLE HEADERS ---
    y = height - 240
    p.setFillColor(colors.HexColor("#F3F4F6"))
    p.rect(40, y, width - 80, 25, fill=1, stroke=0)
    
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, y + 7, "Description")
    p.drawString(320, y + 7, "Qty")
    p.drawString(390, y + 7, "Unit Price")
    p.drawRightString(width - 50, y + 7, "Total")

    # --- 6. ITEMS LOOP ---
    y -= 25
    p.setFont("Helvetica", 10)
    subtotal = Decimal('0.00')

    for item in items:
        if y < 150:
            p.showPage()
            y = height - 50 

        p.drawString(50, y, item.description)
        p.drawString(320, y, str(item.quantity))
        p.drawString(390, y, f"{item.unit_price}")
        
        line_total = Decimal(str(item.quantity)) * Decimal(str(item.unit_price))
        p.drawRightString(width - 50, y, f"{line_total:.2f}")
        
        subtotal += line_total
        y -= 25

    # --- 7. SUMMARY SECTION ---
    y -= 20
    p.setStrokeColor(colors.HexColor("#E5E7EB"))
    p.line(350, y + 10, width - 40, y + 10)
    
    p.setFont("Helvetica", 10)
    p.drawString(350, y - 5, "Subtotal:")
    p.drawRightString(width - 50, y - 5, f"INR {subtotal:.2f}")
    
    grand_total = subtotal
    if request.user.is_premium and invoice.tax_percentage > 0:
        tax_amount = (subtotal * Decimal(str(invoice.tax_percentage))) / 100
        grand_total += tax_amount
        y -= 20
        p.drawString(350, y - 5, f"Tax ({invoice.tax_percentage}%):")
        p.drawRightString(width - 50, y - 5, f"INR {tax_amount:.2f}")

    y -= 35
    p.setFont("Helvetica-Bold", 14)
    p.drawString(350, y, "GRAND TOTAL:")
    p.drawRightString(width - 50, y, f"INR {grand_total:.2f}")

    # --- 8. WATERMARK & FOOTER ---
    if not request.user.is_premium:
        p.setFont("Helvetica-Bold", 60)
        p.setStrokeColor(colors.lightgrey)
        p.setFillColor(colors.HexColor("#F3F4F6"))
        p.saveState()
        p.translate(width/2, height/2)
        p.rotate(45)
        p.drawCentredString(0, 0, "FREE VERSION")
        p.restoreState()

        p.setFillColor(colors.grey)
        p.setFont("Helvetica-Oblique", 8)
        p.drawCentredString(width/2, 40, "Thank you for using InvoiceFlow. Generated professionally.")

    p.showPage()
    p.save()
    return response
