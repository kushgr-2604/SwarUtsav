const WINDOW_MS = 60_000;
const MAX_REQUESTS = 20;
const buckets = new Map();

function isRateLimited(identifier) {
    const now = Date.now();

    if (buckets.size > 2_000) {
        for (const [key, bucket] of buckets) {
            if (now - bucket.startedAt >= WINDOW_MS) buckets.delete(key);
        }
        while (buckets.size > 2_000) buckets.delete(buckets.keys().next().value);
    }

    const current = buckets.get(identifier);
    if (!current || now - current.startedAt >= WINDOW_MS) {
        buckets.set(identifier, { startedAt: now, count: 1 });
        return false;
    }

    if (current.count >= MAX_REQUESTS) return true;
    current.count += 1;
    return false;
}

module.exports = { isRateLimited };
