# Transporter Invoice

ERPNext/Frappe v16 app for company-scoped transport billing.

The app uses a spreadsheet-style transport matrix:

- distance band
- locations covered
- customer rates for `10 MT`, `14 MT`, and `Trailer`
- transporter rates for `10-13 MT`, `14-17 MT`, and `28 MT`

It also supports the separate under-10-tonne table:

- truck capacity `1.5 MT`, `3 MT`, `5 MT`, or `7 MT`
- fixed customer trip rate
- fixed transporter trip rate

One **Transport Rate Card** can be used as a general template. Leave **Customer** and
**Transporter** blank to apply it to any delivery in the enabled company. If a customer
or transporter has a special rate, create another submitted card for the same matrix and
set that Customer and/or Transporter. During delivery entry, the app automatically uses
the most specific matching card first.

Each **Transport Delivery** is one trip. The delivery stores the destination, truck
class, actual weight, selected customer rate, selected transporter rate, customer amount,
transporter amount, and margin.

When a delivery is saved, choose the **Rate Category**:

- **Under 10 Tonnes** uses the fixed truck-capacity rates.
- **10 Tonnes and Above** uses the destination route matrix.

If the rate card is **Per Kg**, invoice quantity is the actual weight in Kg and:

```text
customer amount = actual weight kg * customer rate
transporter amount = actual weight kg * transporter rate
margin = customer amount - transporter amount
```

If the rate card is **Fixed Trip Amount**, invoice quantity is `1` and the rates are used
as full trip amounts. Under-10-tonne rate cards are forced to fixed trip amount.

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
3. Create and submit a general **Transport Rate Card** for **Under 10 Tonnes** if you use
   the small-truck rates.
4. Create and submit a general **Transport Rate Card** for **10 Tonnes and Above** with
   the route matrix rows.
5. Create customer-specific or transporter-specific rate cards only where rates differ.

## Default Rate Cards

After you create **Transport Invoice Settings** for the enabled company, the app seeds two
generic draft rate cards automatically:

- **Under 10 Tonnes** fixed truck-capacity rates.
- **10 Tonnes and Above** route matrix rates.

The same seed also runs on install and migrate, but it checks first so it does not create
duplicates. These cards have no Customer and no Transporter, so they work as templates for
any delivery after you submit them. You can edit, delete, or copy them before submitting,
and you can create more specific customer/transporter overrides when needed.

The delivery date determines which submitted rate card applies, and the selected values
are copied onto each delivery for historical accuracy.

Only one Transport Invoice Settings record is allowed. Its Company becomes the enabled
organization for the whole app; rate cards, deliveries, and billing batches for every
other ERPNext company are rejected. Generated invoices and configured cost centers are
also validated against that enabled company.
