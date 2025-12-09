# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockCountSession(models.Model):
    """
    Stock Count Session - Main model to manage stock counting process.
    """
    _name = "stock.count.session"
    _description = "Stock Count Session"
    _order = "create_date desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    # Basic Fields
    name = fields.Char(
        string="Session Name",
        required=True,
        copy=False,
        readonly=True,
        default="New",
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("in_progress", "In-Progress"),
            ("review", "Review"),
            ("approval", "Approval"),
            ("done", "Done"),
            ("rejected", "Rejected"),
        ],
        default="draft",
        tracking=True,
    )
    note = fields.Text(string="Notes")
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Owner",
        default=lambda self: self.env.user,
    )

    # Date Fields
    date_start = fields.Datetime(
        string="Start Time",
        default=fields.Datetime.now,
    )
    date_end = fields.Datetime(string="End Time")

    count_effective_date = fields.Date(
        string="Count Effective Date",
        default=fields.Date.context_today,
        help="Date used to reflect the Stock Valuation Layer.",
    )
    review_date = fields.Datetime(
        string="Review Date",
        readonly=True,
        copy=False,
    )
    approval_date = fields.Datetime(
        string="Approval Date",
        readonly=True,
        copy=False,
    )
    rejection_date = fields.Datetime(
        string="Rejection Date",
        readonly=True,
        copy=False,
    )
    rejection_reason = fields.Text(
        string="Rejection Reason",
        readonly=True,
        copy=False,
    )

    # Relational Fields
    attendee_ids = fields.Many2many(
        comodel_name="res.users",
        string="Attendees",
        domain="[('share', '=', False)]",
        help="Employees participating in the count process",
    )
    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        string="Warehouse",
    )
    location_id = fields.Many2one(
        comodel_name="stock.location",
        string="Location",
        domain="[('warehouse_id', '=', warehouse_id), ('usage', 'in', ['internal'])]",
    )
    finance_manager_id = fields.Many2one(
        comodel_name="res.users",
        string="Finance Manager",
        tracking=True,
    )
    line_ids = fields.One2many(
        comodel_name="stock.count.line",
        inverse_name="session_id",
        string="Count Lines",
    )

    # Selection Fields
    stock_filter = fields.Selection(
        selection=[
            ("available", "All available quantities"),
            ("include_zero", "Include zero quantities"),
        ],
        string="Stock Filter",
        required=True,
        default="available",
    )

    # Computed Fields  
    is_finance_manager = fields.Boolean(
        string="Is Finance Manager",
        compute="_compute_is_finance_manager",
    )
    line_count = fields.Integer(
        string="Lines",
        compute="_compute_totals",
    )
    qty_counted_total = fields.Float(
        string="Total Counted Qty",
        compute="_compute_totals",
    )
    qty_difference_total = fields.Float(
        string="Total Difference",
        compute="_compute_totals",
    )

    # Calculated Outcomes
    total_diff_qty_positive = fields.Float(
        string="Total Diff Qty (+) Count",
        compute="_compute_calculated_outcomes",
    )
    total_diff_qty_negative = fields.Float(
        string="Total Diff Qty (-) Count",
        compute="_compute_calculated_outcomes",
    )
    total_diff_value_positive = fields.Float(
        string="Total Diff Val (+) Count",
        compute="_compute_calculated_outcomes",
    )
    total_diff_value_negative = fields.Float(
        string="Total Diff Val (-) Count",
        compute="_compute_calculated_outcomes",
    )
    total_diff_value_net = fields.Float(
        string="Total Diff Val (Net)",
        compute="_compute_calculated_outcomes",
    )
    total_diff_review_value_positive = fields.Float(
        string="Review Diff Val (+)",
        compute="_compute_calculated_outcomes",
    )
    total_diff_review_value_negative = fields.Float(
        string="Review Diff Val (-)",
        compute="_compute_calculated_outcomes",
    )
    total_diff_review_value_net = fields.Float(
        string="Review Diff Val (Net)",
        compute="_compute_calculated_outcomes",
    )

    # Compute Methods
    @api.depends("finance_manager_id")
    def _compute_is_finance_manager(self):
        for record in self:
            record.is_finance_manager = (
                self.env.user == record.finance_manager_id
                and self.env.user.has_group("base.group_finance_manager")
            )
    @api.depends("line_ids.qty_counted", "line_ids.qty_difference")
    def _compute_totals(self):
        for record in self:
            record.line_count = len(record.line_ids)
            record.qty_counted_total = sum(record.line_ids.mapped("qty_counted"))
            record.qty_difference_total = sum(record.line_ids.mapped("qty_difference"))
    @api.depends(
        "line_ids.qty_difference",
        "line_ids.count_net_difference_value",
        "line_ids.qty_review_counted",
        "line_ids.product_id.standard_price",
    )
    def _compute_calculated_outcomes(self):
        for record in self:
            lines = record.line_ids

            # Quantity Differences (Positive & Negative)
            record.total_diff_qty_positive = sum(
                line.qty_difference for line in lines if line.qty_difference > 0
            )
            record.total_diff_qty_negative = sum(
                line.qty_difference for line in lines if line.qty_difference < 0
            )

            # Value Differences (Positive, Negative & Net)
            record.total_diff_value_positive = sum(
                line.count_net_difference_value
                for line in lines
                if line.count_net_difference_value > 0
            )
            record.total_diff_value_negative = sum(
                line.count_net_difference_value
                for line in lines
                if line.count_net_difference_value < 0
            )
            record.total_diff_value_net = (
                record.total_diff_value_positive + record.total_diff_value_negative
            )

            # Review Value Differences (Positive, Negative & Net)
            # This calculates the difference based on qty_review_counted only (not qty_counted)
            # Used to show the impact of review adjustments
            review_positive = 0.0
            review_negative = 0.0
            for line in lines:
                # Only calculate if in review state or later and review qty differs from counted qty
                if line.state in ["review", "approval", "done", "rejected"]:
                    diff = line.qty_review_counted - line.qty_system
                    cost = line.product_id.standard_price or 0.0
                    val = diff * cost
                    if val > 0:
                        review_positive += val
                    elif val < 0:
                        review_negative += val

            record.total_diff_review_value_positive = review_positive
            record.total_diff_review_value_negative = review_negative
            record.total_diff_review_value_net = review_positive + review_negative
    
    # Override Methods
    @api.model_create_multi
    def create(self, vals_list):


        """
        Override create to assign sequence number automatically.
        """
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == "New":
                vals["name"] = self.env['ir.sequence'].next_by_code(
                    'stock.count.session'
                ) or "New"
        return super().create(vals_list)
    
    # Action Methods
    def action_generate_lines(self):
        """Generate stock count lines based on warehouse/location selection."""
        self.ensure_one()

        if not self.warehouse_id:
            raise UserError(_("Please select a Warehouse first."))

        self.line_ids.unlink()

        # Build domain dynamically
        domain = []

        if self.location_id:
            domain.append(("location_id", "=", self.location_id.id))
        else:
            location_ids = self.env["stock.location"].search([
                ("warehouse_id", "=", self.warehouse_id.id),
                ("usage", "in", ["internal"]),
            ]).ids

            if not location_ids:
                raise UserError(
                    _("No internal locations found in the selected warehouse.")
                )

            domain.append(("location_id", "in", location_ids))

        if self.stock_filter == "available":
            domain.append(("quantity", ">", 0))

        # Create lines from quants
        quants = self.env["stock.quant"].search(domain)
        vals_list = []
        for quant in quants:
            vals_list.append({
                "session_id": self.id,
                "product_id": quant.product_id.id,
                "location_id": quant.location_id.id,
                "lot_id": quant.lot_id.id,
                "package_id": quant.package_id.id,
                "qty_system": quant.quantity,
                "qty_counted": 0,
            })

        self.env["stock.count.line"].create(vals_list)
        self.state = "in_progress"
    def action_submit_count(self):
        """Submit count for review."""
        for record in self:
            # Copy qty_counted to qty_review_counted as default for review
            for line in record.line_ids:
                line.qty_review_counted = line.qty_counted
            
            record.write({
                "state": "review",
                "review_date": fields.Datetime.now(),
            })

        return True    
    def action_validate(self):
        """Validate and send for approval."""
        for record in self:
            if not record.finance_manager_id:
                raise UserError(_("Please assign a Finance Manager first."))

            record.write({
                "state": "approval",
                "approval_date": fields.Datetime.now(),
            })

            msg = _("Stock Count %s needs approval.") % record.name
            record.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=record.finance_manager_id.id,
                summary=_("Approve Stock Count"),
                note=msg,
            )
        return True
    def action_approved(self):
        """Approve the stock count."""
        for record in self:
            record.write({
                "state": "done",
                "date_end": fields.Datetime.now(),
            })
        return True
    def action_refuse_recount(self):
        """Open refuse wizard for recount."""
        self.ensure_one()
        return self._open_refuse_wizard("recount")
    def action_rejected(self):
        """Open refuse wizard for rejection."""
        self.ensure_one()
        return self._open_refuse_wizard("reject")
    
    #business  methods
    def _open_refuse_wizard(self, action_type):
        """Helper method to open refuse wizard."""
        self.ensure_one()
        return {
            "name": _("Reason"),
            "type": "ir.actions.act_window",
            "res_model": "stock.count.refuse.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_session_id": self.id,
                "default_action_type": action_type,
            },
        }
