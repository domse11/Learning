from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta


class EstatePropertyOffer(models.Model):
    _name = "estate.property.offer"
    _description = "Property Offer"
    _order = "price desc"

    price = fields.Float(string="Price")
    status = fields.Selection(
        [("accepted", "Accepted"), ("refused", "Refused")], string="Status", copy=False
    )
    partner_id = fields.Many2one("res.partner", string="Partner", required=True)
    property_id = fields.Many2one(
        "estate.property", string="Property", required=True, ondelete="cascade"
    )
    validity = fields.Integer(string="Validity (days)", default=7)
    date_deadline = fields.Date(
        string="Deadline",
        compute="_compute_date_deadline",
        inverse="_inverse_date_deadline",
        store=True,
    )

    property_type_id = fields.Many2one(
        related="property_id.property_type_id", store=True
    )

    @api.depends("create_date", "validity")
    def _compute_date_deadline(self):
        for offer in self:
            creation_date = (offer.create_date or fields.Datetime.now()).date()
            offer.date_deadline = creation_date + timedelta(days=offer.validity)

    def _inverse_date_deadline(self):
        for offer in self:
            creation_date = (offer.create_date or fields.Datetime.now()).date()
        if offer.date_deadline:
            offer.validity = (offer.date_deadline - creation_date).days

    # Buttons: Accept / Refuse offer
    def action_accept_offer(self):
        for offer in self:
            if offer.property_id.state == "sold":
                raise UserError("Cannot accept offer for a sold property.")

            if offer.price < 0.9 * offer.property_id.expected_price:
                raise ValidationError(
                    "Selling price must be at least 90% of expected price."
                )

            # Accept this offer
            offer.status = "accepted"
            offer.property_id.state = "offer_accepted"
            offer.property_id.buyer = offer.partner_id
            offer.property_id.selling_price = offer.price

            # Refuse all other offers
            other_offers = offer.property_id.offer_ids.filtered(
                lambda o: o.id != offer.id and o.status != "refused"
            )
            other_offers.write({"status": "refused"})

    def action_refuse_offer(self):
        for offer in self:
            if offer.status == "accepted":
                # If an already accepted offer is refused, reset the sale
                offer.property_id.selling_price = 0.0
                offer.property_id.buyer = False
                offer.property_id.state = "new"  # reset the state if needed
            offer.status = "refused"

    # Status Icons for Tree View
    @api.depends("status")
    def _compute_status_icon(self):
        for offer in self:
            if offer.status == "accepted":
                offer.status_icon = "<span title='Accepted'><i class='fa fa-check text-success'/></span>"
            elif offer.status == "refused":
                offer.status_icon = (
                    "<span title='Refused'><i class='fa fa-times text-danger'/></span>"
                )
            else:
                offer.status_icon = ""

    # Price must be positive
    @api.constrains("price")
    def _check_offer_price(self):
        for offer in self:
            if offer.price <= 0:
                raise ValidationError("Offer price must be strictly positive.")

    property_type_id = fields.Many2one(
        related="property_id.property_type_id", string="Property Type", store=True
    )

    @api.model
    def create(self, vals):
        offer = super().create(vals)
        offer.property_id.state = "offer_received"
        return offer
