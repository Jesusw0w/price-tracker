# Ideas

- Move price data to Amazon's Creators API (needs an Associates account) instead of
  scraping product pages.
- Scheduled job that flags products with no price for several days: links break, listings
  move, products get discontinued.
- Target prices: a `set_target_price` MCP tool and an alert when a product drops below it.
- `is_a_good_deal` MCP tool backed by Bedrock, judging the current price against history.
- Retry with backoff for transient scrape errors.
- Run the scraper as its own service instead of on a home machine.
