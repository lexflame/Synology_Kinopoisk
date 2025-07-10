"""Utility functions for this package."""
import json
import re
import time
from html.parser import HTMLParser
from typing import Any, List, Optional, Union
from xml.etree import ElementTree

from scraper.exceptions import ResultParseError


def strftime(
    timestamp: Union[str, int, float], pattern: str, millisecs: bool = False
) -> str:
    """Format a timestamp with the given pattern."""
    if isinstance(timestamp, str):
        timestamp = float(timestamp)

    if millisecs:
        timestamp /= 1000

    return time.strftime(pattern, time.localtime(timestamp))


def dict_update(d1: dict, d2: dict) -> dict:
    """Recursively update a dictionary."""
    for k, v2 in d2.items():
        v1 = d1.get(k, None)
        if isinstance(v1, dict) and isinstance(v2, dict):
            d1[k] = dict_update(d1[k], v2)
        elif isinstance(v1, list) and isinstance(v2, list):
            d1[k].extend(x for x in v2 if x not in v1)
        else:
            d1[k] = v2

    return d1


def strip(obj: Any) -> Any:
    """Recursively strip a string, list, or dict."""
    if isinstance(obj, list):
        return list(filter(lambda x: x is not None, [strip(i) for i in obj]))
    elif isinstance(obj, dict):
        return {k: strip(v) for k, v in obj.items()}
    elif isinstance(obj, str):
        obj = obj.strip()
        return obj if obj != "" else None
    return obj


def re_sub(obj: Any, pattern: str, repl: str) -> Any:
    """Recursively replace a pattern in a string, list, or dict."""
    if isinstance(obj, list):
        return [re_sub(item, pattern, repl) for item in obj]
    elif isinstance(obj, dict):
        return {k: re_sub(v, pattern, repl) for k, v in obj.items()}
    elif isinstance(obj, str):
        return re.sub(pattern, repl, obj)
    return obj


def str_to_etree(string: str) -> Optional[ElementTree.Element]:
    """Convert a string to an ElementTree."""
    string = string.strip()
    if string.startswith("{") or string.startswith("["):
        return json_to_etree(json.loads(string, strict=False))
    elif string.startswith("<"):
        return html_to_etree(string)
    return None


def json_to_etree(json_obj: Any, tag: str = "root"):
    """Convert a JSON object to an ElementTree."""
    element = ElementTree.Element(tag)
    if isinstance(json_obj, list):
        for i, item in enumerate(json_obj):
            element.append(json_to_etree(item, f"i{str(i)}"))
    elif isinstance(json_obj, dict):
        for k, v in json_obj.items():
            element.append(json_to_etree(v, k))
    elif json_obj is not None:
        element.text = str(json_obj)
    return element


def html_to_etree(html_text: str):
    """Convert an HTML text to an ElementTree."""
    return EtreeHTMLParser().parse(html_text)


class EtreeHTMLParser(HTMLParser):
    """Simple HTML parser that converts HTML to an ElementTree."""

    tag_stack: List[ElementTree.Element]
    cur_tag: Optional[ElementTree.Element]
    after_end: bool

    def __init__(self):
        super().__init__()
        self.tag_stack = []
        self.cur_tag = None
        self.after_end = False

    def handle_starttag(self, tag, attrs):
        self.after_end = False
        self.cur_tag = ElementTree.Element(tag, {k: v or "" for k, v in attrs})
        if len(self.tag_stack) > 0:
            self.tag_stack[-1].append(self.cur_tag)
        self.tag_stack.append(self.cur_tag)

    def handle_endtag(self, tag):
        while any(item.tag == tag for item in self.tag_stack):
            self.after_end = True
            self.cur_tag = self.tag_stack.pop()
            if self.cur_tag.tag == tag:
                break

    def handle_data(self, data):
        if self.cur_tag is not None:
            if self.after_end:
                self.cur_tag.tail = data.strip()
            else:
                self.cur_tag.text = data.strip()

    def error(self, message):
        raise ResultParseError

    def parse(self, html):
        self.feed(html)
        self.close()
        return self.cur_tag
