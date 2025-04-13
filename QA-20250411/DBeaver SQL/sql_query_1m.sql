SELECT 
    toStartOfInterval(timestamp, INTERVAL 1 MINUTE) AS k_time_1m,
    argMin(price, timestamp) AS open_1m,
    max(price) AS high_1m,
    min(price) AS low_1m,
    argMax(price, timestamp) AS close_1m,
    sum(volume) AS volume_1m
FROM 
    your_table_name
WHERE 
    address = '6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfGiPN'
    AND timestamp BETWEEN 'Start: 2025-04-13T04:00:05.029560' AND 'End: 2025-04-13T05:00:05.029560'
GROUP BY 
    k_time_1m