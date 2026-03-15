"""docmind/modules/templates/apiv1/handler.py"""

from fastapi import APIRouter, Depends

from docmind.core.auth import get_current_user
from docmind.core.logging import get_logger

from ..schemas import TemplateListResponse, TemplateResponse

logger = get_logger(__name__)
router = APIRouter()

TEMPLATES = [
    TemplateResponse(
        type="invoice",
        name="Invoice",
        description="Commercial invoices with line items, totals, and vendor info",
        required_fields=["invoice_number", "date", "total_amount", "vendor_name"],
        optional_fields=["due_date", "tax_amount", "line_items", "purchase_order"],
    ),
    TemplateResponse(
        type="receipt",
        name="Receipt",
        description="Purchase receipts with itemized costs",
        required_fields=["date", "total_amount", "merchant_name"],
        optional_fields=["tax_amount", "payment_method", "line_items"],
    ),
    TemplateResponse(
        type="medical_report",
        name="Medical Report",
        description="Medical lab reports and diagnostic documents",
        required_fields=["patient_name", "report_date", "report_type"],
        optional_fields=["doctor_name", "diagnosis", "test_results", "facility"],
    ),
    TemplateResponse(
        type="contract",
        name="Contract",
        description="Legal contracts and agreements",
        required_fields=["parties", "effective_date", "contract_type"],
        optional_fields=["expiry_date", "terms", "signatures", "governing_law"],
    ),
    TemplateResponse(
        type="id_document",
        name="ID Document",
        description="Government-issued identification documents",
        required_fields=["full_name", "document_number", "date_of_birth"],
        optional_fields=["expiry_date", "nationality", "address", "issuing_authority"],
    ),
]


@router.get("", response_model=TemplateListResponse)
async def list_templates(current_user: dict = Depends(get_current_user)):
    return TemplateListResponse(items=TEMPLATES)
