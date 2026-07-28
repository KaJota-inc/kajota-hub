"""Vendor-agnostic helpdesk integration primitives.

Freshdesk, Zendesk, and any future integrations import from here. The load-bearing
distinction is: what's here does not care WHICH helpdesk fired the webhook, only
that the ticket is shaped like `{description, tags, ...}` and we need to extract
an envelope, triage it, and format the result.
"""
