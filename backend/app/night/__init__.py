"""Stateful night-engine primitives.

The package intentionally keeps imports out of ``__init__`` so canonical state can
depend on the durable record models without creating an import cycle.
"""
