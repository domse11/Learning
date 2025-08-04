from odoo import models, fields, api
from datetime import timedelta
from odoo.exceptions import UserError, ValidationError


class EstateProperty(models.Model):
    _name = "estate.property"
    _description = "Real Estate Property"
    _order = "id desc"

    name = fields.Char(required=True)
    description = fields.Text()
    postcode = fields.Char()

    # Default availability date = today + 3 months
    date_availability = fields.Date(
        copy=False, default=lambda self: fields.Date.today() + timedelta(days=90)
    )

    expected_price = fields.Float(required=True)

    # Selling price is readonly and not copied
    selling_price = fields.Float(readonly=True, copy=False)

    property_type_id = fields.Many2one("estate.property.type", string="Property Type")

    tag_ids = fields.Many2many("estate.property.tag", string="Tags")

    # Other info - Salesman and Buyer
    salesman = fields.Many2one(
        "res.users", string="Salesman", default=lambda self: self.env.user
    )
    buyer = fields.Many2one("res.partner", string="Buyer", copy=False)

    offer_ids = fields.One2many("estate.property.offer", "property_id", string="Offers")

    # Default bedrooms = 2
    bedrooms = fields.Integer(default=2)
    living_area = fields.Integer(string="Living Area (sqm)")
    facades = fields.Integer()
    garage = fields.Boolean()
    garden = fields.Boolean()
    garden_area = fields.Integer(string="Garden Area (sqm)")
    garden_orientation = fields.Selection(
        string="Garden Orientation",
        # Garden Orientation selection
        selection=[
            ("north", "North"),
            ("south", "South"),
            ("east", "East"),
            ("west", "West"),
        ],
    )

    active = fields.Boolean(default=True)

    # Field selection
    state = fields.Selection(
        selection=[
            ("new", "New"),
            ("offer_received", "Offer Received"),
            ("offer_accepted", "Offer Accepted"),
            ("sold", "Sold"),
        ],
        required=True,
        copy=False,
        default="new",
    )

    total_area = fields.Integer(
        string="Total Area (sqm)", compute="_compute_total_area", store=True
    )

    best_price = fields.Float(
        string="Best Offer", compute="_compute_best_price", store=True
    )

    @api.depends("living_area", "garden_area")
    def _compute_total_area(self):
        for record in self:
            record.total_area = (record.living_area or 0) + (record.garden_area or 0)

    @api.depends("offer_ids.price", "offer_ids.status")
    def _compute_best_price(self):
        for record in self:
            # Only consider offers with status "accepted"
            accepted_offers = record.offer_ids.filtered(
                lambda offer: offer.status == "accepted"
            )
            prices = accepted_offers.mapped("price")
            record.best_price = max(prices) if prices else 0.0

    @api.onchange("garden")
    def _onchange_garden(self):
        if self.garden:
            self.garden_area = 10
            self.garden_orientation = "north"
        else:
            self.garden_area = 0
            self.garden_orientation = False

        # Button - Canceled

    def action_mark_as_sold(self):
        for record in self:
            if record.state == "canceled":
                raise UserError("Canceled property cannot be sold.")
            record.state = "sold"

        # Button - Sold

    def action_cancel(self):
        for record in self:
            if record.state == "sold":
                raise UserError("Sold property cannot be canceled.")
            record.state = "canceled"

        # Selling Price cannot be lower than 90% of the expected price

    @api.constrains("selling_price", "expected_price")
    def _check_selling_price(self):
        for record in self:
            if (
                record.selling_price
                and record.expected_price
                and record.selling_price < 0.9 * record.expected_price
            ):
                raise ValidationError(
                    "Selling price must be at least 90% of expected price."
                )

        # Expected Price must be positive

    @api.constrains("expected_price")
    def _check_expected_price(self):
        for record in self:
            if record.expected_price <= 0:
                raise ValidationError("Expected price must be strictly positive.")

        # Selling Price must be positive

    @api.constrains("selling_price")
    def _check_selling_price(self):
        for record in self:
            if record.selling_price < 0:
                raise ValidationError("Selling price must be positive.")

    _sql_constraints = [
        (
            "check_expected_price_positive",
            "CHECK(expected_price > 0)",
            "Expected price must be strictly positive.",
        ),
        (
            "check_selling_price_positive",
            "CHECK(selling_price >= 0)",
            "Selling price must be positive.",
        ),
        ("unique_property_name", "UNIQUE(name)", "The property name must be unique."),
    ]
