"""
Scrape a full Substack article and summarize it using the Claude API.
Returns a structured summary dict ready for Notion page creation.
"""

import json
import os
import re
import subprocess
import tempfile
import time

import anthropic

