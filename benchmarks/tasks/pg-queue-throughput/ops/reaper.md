# Stale job reaper

A cron job runs every minute:

```sql
update jobs
set status = 'pending', worker_id = null
where status = 'processing'
  and started_at < now() - interval '10 minutes';
```

Any job whose worker died mid-flight goes back on the queue. Workers therefore do not
need to hold a transaction open for the whole job to stay crash-safe.
