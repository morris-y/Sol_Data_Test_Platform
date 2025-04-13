SELECT * FROM 
    hubble.old_dex_ohlcv_hour
WHERE 
    token = '6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfGiPN'
    AND time BETWEEN '2025-03-14 15:00:00' AND '2025-03-21 20:30:00'
ORDER BY time DESC
LIMIT 1000;