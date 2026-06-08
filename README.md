# Transporter Invoice

ERPNext/Frappe v16 app for company-scoped transport billing.

The app keeps an effective-dated rate card for vehicle capacities below 10 tonnes.
A submitted Transport Delivery freezes the applicable customer and transporter
rates and can create:

- a Sales Invoice for the customer rate; and
- a Purchase Invoice for the transporter rate.

## Installation

From a Frappe v16 bench:

```bash
bench get-app /path/to/transporter_invoice
bench --site your-site install-app transporter_invoice
bench --site your-site migrate
```

## Initial setup

1. Create non-stock service Items for customer transport income and transporter cost.
2. Create one **Transport Invoice Settings** record for the target company.
3. Create and submit a **Transport Rate Card** with effective dates and rate rows.
4. Create a **Transport Delivery**, fetch the rate, attach proof of delivery, and submit it.
5. Use **Create Both Invoices** from the submitted delivery.

The initial below-10-tonne rate rows from the supplied image are:

| Capacity | Customer rate | Transporter rate | Margin |
| ---: | ---: | ---: | ---: |
| 1.5 | 7,800 | 6,100 | 1,700 |
| 3.0 | 8,200 | 6,800 | 1,400 |
| 5.0 | 11,200 | 8,800 | 2,400 |
| 7.0 | 12,500 | 10,000 | 2,500 |

Create a separate card when rates change. The delivery date determines which submitted
card applies, and the selected values are copied onto the delivery for historical accuracy.

Only one Transport Invoice Settings record is allowed. Its Company becomes the enabled
organization for the whole app; rate cards and deliveries for every other ERPNext company
are rejected. Generated invoices and configured cost centers are also validated against
that enabled company.
