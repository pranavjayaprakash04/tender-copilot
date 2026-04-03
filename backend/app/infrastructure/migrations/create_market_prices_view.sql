CREATE MATERIALIZED VIEW IF NOT EXISTS market_prices AS
SELECT
  COALESCE(category, 'unknown') as tender_category,
  portal,
  AVG(estimated_value) as avg_estimated_value,
  MIN(estimated_value) as min_value,
  MAX(estimated_value) as max_value,
  COUNT(*) as sample_count,
  NOW() as last_refreshed
FROM tenders
WHERE estimated_value IS NOT NULL
  AND estimated_value > 0
GROUP BY COALESCE(category, 'unknown'), portal;

CREATE UNIQUE INDEX IF NOT EXISTS idx_market_prices_pk 
ON market_prices(tender_category, portal);
