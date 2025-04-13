SELECT 
    toStartOfInterval(timestamp, INTERVAL 1 HOUR) AS k_time_1h,
    argMin(price, timestamp) AS open_1h,
    max(price) AS high_1h,
    min(price) AS low_1h,
    argMax(price, timestamp) AS close_1h,
    sum(volume) AS volume_1h
FROM 
    your_table_name
WHERE 
    address = '6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfGiPN'
    AND timestamp BETWEEN 'Start: 2025-04-13T04:00:05.029560' AND 'End: 2025-04-13T05:00:05.029560'
GROUP BY 
    k_time_1h