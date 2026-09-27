# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Three confirmed roles inside the finance/HR operation of Colégio Bernoulli:

- **Usuário do RH** — imports the `.xlsx`/`.xlsm` activity lists after each exam, enters
  the services that did not come from a spreadsheet, and resolves the entries the system
  flags as inconsistent. Highest-volume user of the product.
- **Administrador financeiro** — maintains the single applicator registry (personal,
  academic and banking data) that previously lived in scheduling spreadsheets scattered
  per unit.
- **Gestor financeiro** — reviews the consolidated per-applicator summary, filters by unit
  and paying company, and exports the final workbook for accounting.

**Use scene (confirmed):** desktop, in an office, on a large monitor. Phone and tablet
support is a nice-to-have and never the design target; screen density should be tuned for
big screens rather than compromised for small ones.

## Product Purpose

ProvaPay replaces a manual, spreadsheet-based process for paying the freelance exam
applicators (*aplicadores de prova*) who work for Colégio Bernoulli under RPA
(Recibo de Pagamento Autônomo). Today the work is split across two uncontrolled Excel
files — one for applicator registration/scheduling, one for checking entries, amounts and
units — which is error-prone and hard to audit.

The product unifies both into one database and one web interface: import or enter the
activities performed per applicator, event, date and school unit; derive the gross RPA
amount and the INSS/ISS/IR withholdings from the net amount actually received; and
consolidate what each applicator is owed. Success is a fortnightly closing that is more
reliable, more traceable and faster than the spreadsheet flow it replaces.

## Positioning

The mechanism a neighbouring payroll tool could not truthfully copy: ProvaPay computes
**backwards from the net amount**. The operation negotiates and records what the applicator
actually receives; gross and withholdings are derived (`bruto = líquido ÷ (1 − INSS − ISS − IR)`),
not entered. It then reproduces the manual cross-check the finance team performed by hand —
recalculating each entry and flagging disagreement between the recorded and recomputed net —
and groups payables the way the operation actually pays them: by payment date, applicator and
paying company.

## Operating Context

- **Fortnightly closing cycle.** Activity on or before the 15th is paid on the 5th of the
  following month; activity after the 15th is paid on the 20th. Payment-date cohorts are the
  organising unit of the summary and the export.
- **Source documents.** Activity lists arrive as `.xlsx`/`.xlsm` workbooks in the
  "Relatório de Atividade" layout, one sheet per event. Sheets carry inconsistencies:
  unknown applicators, possible duplicates, missing fields.
- **Administrative structure.** Each school unit maps to a paying company
  (Lourdes → RRPM Matriz, Cidade Jardim → RRPM CJ, Santo Antônio → RRPM GO,
  Vale do Sereno → RRPM VSE). A requesting sector is recorded per activity.
- **Terminal step.** The finished workbook is handed to accounting; the export is the
  product's real output, not a convenience feature.
- **Language.** Portuguese (pt-BR) throughout — interface, data and documents.

## Capabilities and Constraints

- Roles per activity: `APLICADOR`, `ORIENTADOR`, `VOLANTE`.
- Tax rates are editable settings (`TaxSettings`), currently INSS 11%, ISS 5%, IR 0%.
  Already-recorded entries retain the rates in force when they were written.
- The legacy spreadsheet's −R$0,01 adjustment is deliberately **not** reproduced, by
  decision of the finance department.
- Applicators arriving from an import that the registry does not know are created and
  marked *cadastro incompleto* rather than rejected.
- Unknown-but-plausible duplicate rows are surfaced and pre-unchecked, never silently merged.
- Stack is fixed by the existing codebase: Django 5.2 + Django Templates, hand-written CSS
  and vanilla JavaScript, no frontend framework and no build step. PostgreSQL in
  deployment, SQLite locally. A REST API exists alongside the HTML pages.

## Brand Commitments

- **Name and voice:** "ProvaPay". Interface copy is Portuguese, plain and operational —
  it names the accounting reality directly (*lançamento*, *líquido*, *bruto (RPA)*,
  *empresa pagadora*) rather than softening it into generic product language.
- **Institutional identity is binding (confirmed).** The interface must read as a
  Colégio Bernoulli system.
- **"Verde Bernoulli" `#009E8E`** is the school's brand colour and the anchor of this
  product's palette (supplied by the team). Colégio Bernoulli's own mark is a filled
  verde circle carrying a white infinity symbol beside the words "Bernoulli" / "Colégio";
  the infinity is the school's defining motif.
- **ProvaPay has its own supplied mark.** `static/img/logomark.png` is the team's own
  ProvaPay logo: a "PP" monogram in verde where the two P bowls interlock into a lemniscate,
  so the infinity that signs the school is formed by the doubled P of ProvaPay. It is
  artwork supplied by the team, not generated — use it as given. The source render is
  `provapay-01.png` at the repository root; the shipped asset is that artwork trimmed to
  its bounds, alpha-extracted, and normalised to exactly `#009E8E`. Aspect is 1.435:1
  (630×439) — it is a horizontal lockup, never forced into a square.
  `static/img/favicon.png` is the same artwork centred on a square transparent canvas.
- **Constraint that governs every future use of the brand colour:** `#009E8E` is 3.34:1 on
  white. It is a fill, stroke and mark colour — never text on a light surface. Brand text
  uses the darker `#047569`.
- **Resolved (was open).** The shipped visual system began as a port of the Maybe
  personal-finance design system. Its neutral scale, spacing and shadow structure remain;
  the colour identity has been replaced with the verde Bernoulli system described above,
  and the Maybe account-group chart palette has been retired. DESIGN.md records the
  resulting system and its provenance.

## Evidence on Hand

- `README.md` — objective, the eight user stories, the business-rule table, UML.
- `enunciado do trabalho.md` — the assignment this was built for.
- `apps/payroll/calculator.py`, `schedule.py` — the gross-up and payment-date rules.
- `docs/samples/lista_pagamento_exemplo.xlsx` — a representative source workbook.

## Delivery Context

Built as **TP1 for Engenharia de Software** by a four-person team (Ana Clara dos Anjos
Patrício de Novais, Bernardo Pedroso Magalhães, Bernardo Zschaber Morato Nogueira,
Lucas Ferreira Marinho). The confirmed destiny is a **graded classroom deliverable**, not a
production pilot: a 10-minute in-class demo plus a slide deck on AI-agent usage.

Grading weights UI quality heavily — *"Implementação das histórias e qualidade da UI"* is
7 of the 15 points, more than any other single criterion. Design effort here is scored
work, and the demo screens are the ones that get seen: the dashboard, the entry list, the
import preview and the per-applicator summary.