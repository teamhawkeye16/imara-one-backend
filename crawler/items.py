"""
IMARA ONE Crawler Items
"""

import scrapy


class ImaraWebPageItem(scrapy.Item):
    url = scrapy.Field()
    canonical_url = scrapy.Field()
    title = scrapy.Field()
    meta_description = scrapy.Field()
    clean_text = scrapy.Field()
    content_hash = scrapy.Field()
    language = scrapy.Field()
    http_status = scrapy.Field()
    word_count = scrapy.Field()
    domain = scrapy.Field()
    discovered_links = scrapy.Field()

