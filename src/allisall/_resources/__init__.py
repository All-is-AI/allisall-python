"""The operation groups of `Allisall` and `AsyncAllisall`, one module per group.

Each module holds a class for each client. The two build every call through the same
functions, in `_request.py` and `_transport.py`, and differ only in how they send and wait.
"""
