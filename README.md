# Transporter Invoice

ERPNext/Frappe v16 app for company-scoped transport billing.

The app uses a spreadsheet-style transport matrix:

- distance band
- locations covered
- customer rates for `10 MT`, `14 MT`, and `Trailer`
- transporter rates for `10-13 MT`, `14-17 MT`, and `28 MT`

One **Transport Rate Card** can be used as a general template. Leave **Customer** and
**Transporter** blank to apply it to any delivery in the enabled company. If a customer
or transporter has a special rate, create another submitted card for the same matrix and
set that Customer and/or Transporter. During delivery entry, the app automatically uses
the most specific matching card first.

Each **Transport Delivery** is one trip. The delivery stores the destination, truck
class, actual weight, selected customer rate, selected transporter rate, customer amount,
transporter amount, and margin.

When a delivery is saved, the app finds the matching matrix row by destination and truck
class. If the rate card is **Per Kg**, invoice quantity is the actual weight in Kg and:

```text
customer amount = actual weight kg * customer rate
transporter amount = actual weight kg * transporter rate
margin = customer amount - transporter amount
```

If the rate card is **Fixed Trip Amount**, invoice quantity is `1` and the rates are used
as full trip amounts.

## Monthly Billing Model

Use this flow when the customer is billed once per month:

1. Create one **Transport Delivery** for every trip.
2. Submit the delivery after proof of delivery is attached.
3. Create a **Purchase Invoice** from each delivery when you need to pay the rider,
   driver, or vehicle owner.
4. At month end, create a **Transport Billing Batch** for the customer and period.
5. Click **Get Unbilled Deliveries** to pull all submitted trips not yet billed to the customer.
6. Submit the batch.
7. Click **Create Sales Invoice** to create one customer invoice with one line per trip.

The generated Sales Invoice is written back to every included Transport Delivery, so the
same trip cannot be billed to the customer twice.

For audit:

- Monthly Sales Invoice header links to the **Transport Billing Batch**.
- Each monthly Sales Invoice item links to the exact **Transport Delivery** trip.
- Each transporter Purchase Invoice header and item links to the **Transport Delivery**.

## Installation

From a Frappe v16 bench:

```bash
bench get-app /path/to/transporter_invoice
bench --site your-site install-app transporter_invoice
bench --site your-site migrate
```

## Initial Setup

1. Create non-stock service Items for customer transport income and transporter cost.
2. Create one **Transport Invoice Settings** record for the target company.
3. Create and submit a general **Transport Rate Card** with effective dates and route
   matrix rows.
4. Create customer-specific or transporter-specific rate cards only where rates differ.

The delivery date determines which submitted rate card applies, and the selected values
are copied onto each delivery for historical accuracy.

Only one Transport Invoice Settings record is allowed. Its Company becomes the enabled
organization for the whole app; rate cards, deliveries, and billing batches for every
other ERPNext company are rejected. Generated invoices and configured cost centers are
also validated against that enabled company.
