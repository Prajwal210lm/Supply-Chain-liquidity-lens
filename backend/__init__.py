"""Liquidity Lens reasoning layer.

The deterministic nodes (Validate, Compute) live here and produce the FACT
objects the LLM nodes will later reason over. No node may invent a number; the
LLM only cites facts produced here.
"""
