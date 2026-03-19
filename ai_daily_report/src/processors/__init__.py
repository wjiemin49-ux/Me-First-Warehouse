"""Processors package"""
from .cleaner import Cleaner
from .deduper import Deduplicator
from .sorter import Sorter
from .translator import Translator

__all__ = ['Cleaner', 'Deduplicator', 'Sorter', 'Translator']
