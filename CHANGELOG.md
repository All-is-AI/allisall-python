# Changelog

## 0.4.0 (2026-11-10)

* Built against API version 0.4.0
* Ingest unchanged

### ⚠ BREAKING CHANGES

* **sdk:** In TypeScript and Python, these response types gain required members, so code that constructs them, such as a test double, must set them: Client and ClientDetail gain renewal_term, Renewal gains calculation_id and renewal_term, and RenewalList gains today, page and total. The Python SDK also refuses a response without them, so it needs API version 0.4.0. The Go SDK is not affected: the new fields are pointers or zero values, and a struct literal or a response that omits them leaves them unset. From API version 0.4.0 the API refuses a new renewal date before yesterday in UTC on create and update; sending back the renewal_date a read returned is still accepted and keeps the client's schedule. Renewals that share a date are ordered by name without regard to letter case. An earlier SDK walks the renewals list without today, so a later page it reads after midnight UTC is refused with 400 invalid_value on cursor; start the walk again from the first page.
* **sdk:** AttributedEvent gains the required members created_at, import_batch_id, client_id and client_name. In TypeScript and Python, code that constructs an AttributedEvent, such as a test double, must set them. The Python SDK also refuses an event list without them, the client drill-down included, so it needs API version 0.4.0. The Go SDK is not affected: a struct literal that omits the new fields still compiles, and a response from an older server leaves them zero or nil.
* **sdk:** From API version 0.4.0 the API refuses, with 409 client_key_in_use, on create and update, a client_key that another client already holds in any letter case or surrounding whitespace. It refuses an import whose file name is longer than 255 characters, counted as Unicode code points after a directory part separated by / is dropped, with 400 too_long on the file part, on preview and commit. This holds whichever SDK version sends the request.
* **sdk:** Report, ReportSummary and ReportWithPreview rename the letterhead's client_name and workspace_name to letterhead_client_name and letterhead_workspace_name, and ReportPatch renames the members it takes. client_name now holds the client's name as the client record has it. In TypeScript, code that reads workspace_name, or a ReportPatch literal with the old names, no longer compiles; and CalculationSummary, Report, ReportSummary and ReportWithPreview gain required members, so code that constructs them, such as a test double, must set them. In Python, report.workspace_name raises AttributeError and mypy refuses a ReportPatch with the old keys, which the API refuses with 400 unknown_field if sent; the same four types gain required members, which code that constructs them must set, and the SDK refuses a report or a calculation summary without them, so it needs API version 0.4.0. In Go, code that names WorkspaceName on Report, ReportSummary or ReportWithPreview, or ClientName or WorkspaceName on ReportPatch, no longer compiles; the new fields are plain values, so a struct literal that omits them still compiles, and a response from an older server leaves them at their zero values. An earlier SDK that edits a letterhead gets 400 unknown_field from API version 0.4.0, and an earlier Python SDK cannot read a report from it.
* **sdk:** in TypeScript and Python, ClientList, AgentList, ValueModelList and CostLineItemList gain the required members page and total, and ValueModel gains archived_at, so code that constructs them, such as a test double, must set them. The Python SDK also refuses a response without them, so it needs API version 0.4.0. The Go SDK is not affected: the new fields are pointers, and a struct literal or a response that omits them leaves them nil.

### Features

* **sdk:** filter and number the renewals list, and give clients a renewal term
* **sdk:** list and read imports, and send a read mapping back
* **sdk:** list the workspace's calculations and reports, and rename the report letterhead
* **sdk:** list the workspace's events, summarise them and follow their arrivals
* **sdk:** read the workspace and the guided setup's progress, and set its skipped steps
* **sdk:** search, filter and number the pages of the client, agent, value model and cost line item lists

## 0.2.0 (2026-11-02)

* Built against API version 0.2.0
* Ingest unchanged

### ⚠ BREAKING CHANGES

* **sdk:** these response types gain required members, so code that constructs them, such as a test double, must set them. The Python SDK refuses a response without them, so it needs an API that sends them (API version 0.2.0). The API now lists at most 100 entries (1,000 clients) in these lists, and orders manual_lines and partially_covered_line_items by amount.
* **sdk:** ImportPreview gains a required member, so code that constructs one, such as a test double, must set it. The Python SDK refuses a preview response without it, so it needs an API that sends it (API version 0.2.0). The API now refuses event text over 200 characters.

### Features

* **sdk-py:** add the resource clients for every operation
* **sdk-py:** generate the wire types and decode money exactly
* **sdk-py:** send any operation, with retries, options, pagination and CSV upload
* **sdk:** add ignored_columns_omitted to the import preview
* **sdk:** count the entries each capped response list leaves out
* **sdk:** list a calculation's reports as summaries without disclosures


### Bug Fixes

* **sdk:** pack ingest batches into bodies of at most 4,000,000 bytes

## 0.1.0 (2026-10-30)

* Built against API version 0.1.0
* First release

### Miscellaneous Chores

* **sdk:** publish the SDKs from their public repositories
