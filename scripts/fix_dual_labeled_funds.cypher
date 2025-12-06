// Fix nodes that have both Company and Fund labels - remove Company label
MATCH (n)
WHERE 'Company' IN labels(n) AND 'Fund' IN labels(n)
REMOVE n:Company
RETURN n.company_id as company_id, n.name as name, labels(n) as labels
LIMIT 100;

