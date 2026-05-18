# Initial Assessment Memo — Helios / Adriatic Advisory (EXAMPLE)

> **Note:** This is a fully populated *example memo* based on the fictional
> workshop data in `../sample-docs/`. It serves as a reference for the
> draft produced by the agent.

---

## 1. Header

| Field | Value |
|---|---|
| Client | Helios Industrieanlagen GmbH, Stuttgart |
| Engagement ID | BPW-2025-HEL-001 |
| Reporting period | Fiscal year 2025 (2025-01-01 – 2025-12-31) |
| Responsible partner | Dr. Lena Hartmann |
| Memo author | M. Lehmann (Senior Manager, Forensic) |
| Date | 2026-03-08 |
| Confidentiality level | Strictly confidential |
| Memo version | 1.0 |

## 2. Trigger of the memo

On 2026-02-14, the Helios audit committee received an anonymous notice
containing concrete indicators of possible corruption payments routed
through a Croatian advisory company. On 2026-02-19, Mr. Marko Schneider
(Deputy Head of Internal Audit) additionally raised a corresponding initial
suspicion with Compliance. Both reports are consistent in substance.

## 3. Facts of the case

**Documented and verifiable:**

- Between 11/2024 and 12/2025, 9 invoices from Adriatic Advisory d.o.o.
  (Split, HR) totalling **EUR 740,000** were settled
  *(source: ledger extract, account 4710, INV-AA-2024-01 to INV-AA-2025-04)*.
- 4 invoices are booked as **monthly retainers** (EUR 50,000 each),
  3 invoices as **success fees** (EUR 168,000, 96,000, 176,000) with
  an exact reference to three public-sector heating contracts in Croatia
  and Bosnia and Herzegovina (Zagreb-UKC, Sarajevo-Barracks, Split-UKC)
  awarded to Helios in 2025 *(source: ledger extract, contract excerpt §3)*.
- All 9 invoices were approved solely by Mr. K. Petrović (Regional Sales
  Director SEE); the **second signature from Legal required by group policy
  BR-COM-02 §7 is missing in every case** *(source: ledger extract, group
  policy BR-COM-02 §7 para. 3)*.
- The consultancy agreement (§3) explicitly stipulates that **no proof of
  deliverables is a precondition for payment** *(source: contract excerpt
  §3)*. Group policy BR-COM-02 §7 para. 4, by contrast, explicitly requires
  documented proof of deliverables.
- Ms. A. Berger (Procurement Lead SEE) confirmed in the interview on
  2026-03-04 that **no written deliverables** exist and that her request
  for consultant reports went unanswered *(source: file note Berger,
  2026-03-04)*.

**Currently unconfirmed:**

- Personal relationship between Mr. Petrović and the Adriatic CEO
  Mr. T. Marić (mentioned as a rumour in the Berger interview; not
  substantiated).
- Direct causal link between the advisor payments and the award decisions
  of the three public-sector contracting authorities.

## 4. Persons involved and their functions

| Name | Function at client | Role in the matter | Source |
|---|---|---|---|
| K. Petrović | Regional Sales Director SEE | Sole approver of all 9 invoices; signatory of the consultancy agreement without a second signature | Ledger, contract |
| A. Berger | Procurement Lead SEE | Did not commission the engagement; request for deliverables went unanswered | File note 03/04 |
| Ms. Klein | Accounting | Formal release of the invoices | File note 03/04 |
| M. Schneider | Deputy Head of Internal Audit | First internal whistleblower | Email 02/19 |
| Dr. Bauer | Compliance Officer, Helios | Recipient of the report | Email 02/19 |

## 5. Legal assessment — potentially violated provisions

1. **§ 334 StGB i. V. m. IntBestG (bribery of foreign public officials).**
   Elements prima facie satisfied: success-based payments with an exact
   link to award decisions of foreign public-sector contracting
   authorities; missing documentation of the advisory services.
   *Risk classification per IDW PS 210:* indirectly relevant, but with
   potentially material indirect effects.
2. **§ 30 OWiG i. V. m. § 130 OWiG (corporate fine, breach of supervisory
   duties).** Elements prima facie satisfied: violation of internal
   controls (second signature, proof of deliverables); de facto
   circumvention of the company's own group policy.
3. **Group policy BR-COM-02 §7 — internal violation.** Second signature
   missing in 9 of 9 cases; proof of deliverables missing in 9 of 9 cases;
   success fees in the public sector were not approved by the management
   board.

## 6. Materiality for the financial statements

- **Direct effects:** EUR 740,000 recorded as expense, recoverability
  uncertain. Possible provisions for fines (§ 30 OWiG: up to EUR 10 million
  plus disgorgement of the economic benefit; the disgorgement amount is
  benchmarked against the three award projects with EUR 11.0 million in
  contract volume). **Material.**
- **Indirect effects:** reputational damage, possible EU-level debarment
  (breach of Art. 38 Directive 2014/24/EU), risk to ongoing public
  contracts, going-concern aspects. **High.**

## 7. Required next steps

| # | Action | Owner | Due | Status |
|---|---|---|---|---|
| 1 | Extended journal entry testing on account 4710 and related accounts | M. Lehmann | 2026-03-22 | open |
| 2 | Forensic email analysis Petrović ↔ Marić (coordinated with Helios Legal) | external IT forensics team | 2026-04-05 | open |
| 3 | In-depth interview with Petrović (with external legal counsel) | Dr. Hartmann | 2026-03-25 | open |
| 4 | Briefing of the Audit Committee and Helios Supervisory Board | Dr. Hartmann | 2026-03-15 | open |
| 5 | Assessment of reporting obligations (§ 138 AO, possibly § 261 StGB money laundering) | external legal counsel | 2026-03-20 | open |

## 8. Escalation and information

| Recipient | Function | Date informed | Form |
|---|---|---|---|
| Dr. Hartmann | Engagement Partner | 2026-03-08 | verbal + memo |
| Audit Committee Helios | Client | planned 2026-03-15 | written submission |
| Beispiel & Partner — Risk Management | firm-side | 2026-03-08 | email with memo attachment |

## 9. Documentation notes

- [x] Memo filed in the audit-grade DMS (`/engagements/BPW-2025-HEL-001/forensic/`)
- [x] Attachments fully referenced
- [x] Access to the memo restricted on a need-to-know basis (Hartmann, Lehmann, Risk Management)

## 10. Approval

| Role | Name | Date | Signature / approved |
|---|---|---|---|
| Author | M. Lehmann | 2026-03-08 | ✓ |
| Engagement Partner | Dr. L. Hartmann | 2026-03-09 | ✓ (HITL gate) |
| Compliance / Risk (firm-side) | C. Vogel | 2026-03-09 | ✓ |
