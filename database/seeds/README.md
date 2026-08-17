# Supply-chain demo seed contract

The teaching demo database must expose these business areas:

- suppliers and supplier delivery performance
- purchase orders and purchase-order lines
- materials and bills of material
- production work orders and completion records
- batches and traceability
- inventory balances and shortage risk
- quality inspections and non-conformance
- sales orders and order lines
- delivery plans and fulfillment milestones

Seed scripts must be versioned, repeatable, and idempotent. They must create a
dedicated read-only account for analysis examples and must never be used as the
platform database seed. The current platform demo seed remains in
`backend/app/main.py` until the tenancy module extraction is complete.
