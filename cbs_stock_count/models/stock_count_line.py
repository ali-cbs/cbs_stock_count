# -*- coding: utf-8 -*-

import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class StockCountLine(models.Model):
    """
    Stock Count Line - Individual line items for stock counting.
    """
    _name = "stock.count.line"
    _description = "Stock Count Line"

    # Relational Fields
    session_id = fields.Many2one(
        comodel_name="stock.count.session",
        required=True,
        ondelete="cascade",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        required=True,
    )
    product_category_id = fields.Many2one(
        related="product_id.categ_id",
        string="Category",
        store=True,
    )
    location_id = fields.Many2one(
        comodel_name="stock.location",
        required=True,
    )
    lot_id = fields.Many2one(
        comodel_name="stock.lot",
        string="Lot/Serial",
    )
    package_id = fields.Many2one(
        comodel_name="stock.quant.package",
        string="Package",
    )
    uom_id = fields.Many2one(
        related="product_id.uom_id",
        string="UoM",
    )
    scanned_by = fields.Many2one(
        comodel_name="res.users",
        string="Scanned By",
        default=lambda self: self.env.user,
    )

    # Quantity Fields
    qty_system = fields.Float(
        string="System Qty",
        readonly=True,
    )
    qty_counted = fields.Float(string="Counted Qty")
    qty_review_counted = fields.Float(string="Review Counted Qty")
    qty_difference = fields.Float(
        string="Difference",
        compute="_compute_difference",
        store=True,
    )

    # Value Fields
    product_value_before = fields.Float(
        string="Value Before",
        compute="_compute_values",
        store=True,
    )
    count_net_difference_value = fields.Float(
        string="Net Diff Value",
        compute="_compute_values",
        store=True,
    )
    variant_percentage_value = fields.Float(
        string="Var %",
        compute="_compute_values",
        store=True,
    )
    accepted_product_diff_kpi = fields.Float(
        related="product_category_id.accepted_diff_kpi_percent",
        string="KPI %",
        readonly=True,
    )

    # Audit Fields
    barcode_scanned = fields.Char(string="Scanned Barcode")
    scanned_at = fields.Datetime(
        string="Scanned At",
        default=fields.Datetime.now,
    )
    note = fields.Char(string="Note")
    state = fields.Selection(
        related="session_id.state",
        store=True,
    )

    # Compute Methods
    @api.depends("qty_system", "qty_counted", "qty_review_counted", "state")
    def _compute_difference(self):
        """Calculate quantity difference based on state and available quantities."""
        for line in self:
            if line.state in ["review", "approval", "done", "rejected"]:
                # In review/approval states, use qty_review_counted
                # qty_review_counted should be pre-populated with qty_counted when entering review state
                line.qty_difference = line.qty_review_counted - line.qty_system
            else:
                # Draft or In-Progress state - use qty_counted
                line.qty_difference = line.qty_counted - line.qty_system

            _logger.debug(
                "Line %s: Difference = %s (System: %s, Counted: %s, Review: %s, State: %s)",
                line.id,
                line.qty_difference,
                line.qty_system,
                line.qty_counted,
                line.qty_review_counted,
                line.state,
            )

    @api.depends("qty_difference", "qty_system", "product_id.standard_price")
    def _compute_values(self):
        """Calculate values and percentages."""
        for line in self:
            cost = line.product_id.standard_price or 0.0

            # 1. Product value before count
            line.product_value_before = line.qty_system * cost

            # 2. Net difference value
            line.count_net_difference_value = line.qty_difference * cost

            # 3. Variance percentage
            if line.qty_system and abs(line.qty_system) > 0:
                percentage = (abs(line.qty_difference) / abs(line.qty_system)) * 100.0
                line.variant_percentage_value = round(percentage, 2)
            else:
                # System qty is zero
                if abs(line.qty_difference) > 0.001:
                    line.variant_percentage_value = 100.0
                else:
                    line.variant_percentage_value = 0.0


