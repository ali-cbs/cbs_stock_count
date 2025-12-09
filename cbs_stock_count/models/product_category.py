# -*- coding: utf-8 -*-

from odoo import models, fields


class ProductCategory(models.Model):
    """
    Extends Product Category to add KPI percentage for stock counting.
    Requirement 11: Add KPI percentage per product category.
    """
    _inherit = "product.category"

    accepted_diff_kpi_percent = fields.Float(
        string="KPI %",
        help="Allowed percentage of difference before flagging.",
        default=0.0,
    )
