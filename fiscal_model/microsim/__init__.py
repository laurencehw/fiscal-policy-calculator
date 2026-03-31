"""Microsimulation engine for tax policy analysis."""

from .data_generator import SyntheticPopulation
from .engine import MicroTaxCalculator

__all__ = ["MicroTaxCalculator", "SyntheticPopulation"]
