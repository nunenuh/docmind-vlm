"""Unit tests for template services."""

from docmind.modules.templates.services import TemplateFieldService


class TestTemplateFieldService:
    """Tests for TemplateFieldService."""

    def setup_method(self):
        self.service = TemplateFieldService()

    def test_normalize_dict_fields(self):
        fields = [
            {"key": "nik", "label": "NIK", "type": "string", "required": True},
            {"key": "nama", "label": "Nama"},
        ]
        result = self.service.normalize_fields(fields)
        assert len(result) == 2
        assert result[0]["key"] == "nik"
        assert result[0]["label"] == "NIK"
        assert result[0]["type"] == "string"
        assert result[0]["required"] is True
        assert result[1]["key"] == "nama"
        assert result[1]["required"] is True  # default

    def test_normalize_string_fields(self):
        fields = ["field_a", "field_b"]
        result = self.service.normalize_fields(fields)
        assert len(result) == 2
        assert result[0]["key"] == "field_a"
        assert result[0]["label"] == "field_a"
        assert result[0]["type"] == "string"
        assert result[0]["required"] is True

    def test_normalize_empty(self):
        assert self.service.normalize_fields([]) == []

    def test_get_required_field_keys(self):
        fields = [
            {"key": "a", "required": True},
            {"key": "b", "required": False},
            {"key": "c", "required": True},
        ]
        result = self.service.get_required_field_keys(fields)
        assert result == ["a", "c"]

    def test_get_optional_field_keys(self):
        fields = [
            {"key": "a", "required": True},
            {"key": "b", "required": False},
            {"key": "c", "required": False},
        ]
        result = self.service.get_optional_field_keys(fields)
        assert result == ["b", "c"]

    def test_guess_category_identity(self):
        assert self.service.guess_category("ktp") == "identity"
        assert self.service.guess_category("kk") == "identity"
        assert self.service.guess_category("sim") == "identity"

    def test_guess_category_vehicle(self):
        assert self.service.guess_category("stnk") == "vehicle"
        assert self.service.guess_category("bpkb") == "vehicle"

    def test_guess_category_tax(self):
        assert self.service.guess_category("npwp") == "tax"
        assert self.service.guess_category("faktur_pajak") == "tax"

    def test_guess_category_finance(self):
        assert self.service.guess_category("invoice") == "finance"
        assert self.service.guess_category("receipt") == "finance"
        assert self.service.guess_category("slip_gaji") == "finance"

    def test_guess_category_legal(self):
        assert self.service.guess_category("contract") == "legal"
        assert self.service.guess_category("surat_kuasa") == "legal"

    def test_guess_category_unknown(self):
        assert self.service.guess_category("random_doc") == "general"
        assert self.service.guess_category("") == "general"
