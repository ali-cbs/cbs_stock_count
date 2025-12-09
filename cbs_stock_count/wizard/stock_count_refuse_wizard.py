# -*- coding: utf-8 -*-

from odoo import models, fields


class StockCountRefuseWizard(models.TransientModel):
    """Wizard for refusing/rejecting stock count sessions."""
    _name = "stock.count.refuse.wizard"
    _description = "Stock Count Refuse Wizard"

    session_id = fields.Many2one(
        comodel_name="stock.count.session",
        required=True,
    )
    reason = fields.Text(
        string="Reason",
        required=True,
    )
    action_type = fields.Selection(
        selection=[
            ("recount", "Recount"),
            ("reject", "Reject"),
        ],
        required=True,
    )

    def action_confirm(self):
        """Confirm the refuse/reject action."""
        self.ensure_one()
        session = self.session_id
        session.message_post(
            body=f"Action: {self.action_type}. Reason: {self.reason}"
        )

        if self.action_type == "recount":
            session.write({"state": "in_progress"})
        elif self.action_type == "reject":
            session.write({
                "state": "rejected",
                "rejection_date": fields.Datetime.now(),
                "rejection_reason": self.reason,
            })

        return {"type": "ir.actions.act_window_close"}
