# Pipeline — Reference

## Docker Mount Examples

```yaml
services:
  etl:
    image: synthex/etl:latest
    volumes:
      # Bind mount (development)
      - ./scripts:/app/scripts:ro
      # Named volume (persistent data)
      - data_volume:/app/data
      # tmpfs for scratch (ephemeral, fast)
      - type: tmpfs, target: /app/scratch
      # Host path with SELinux context
      - /mnt/nfs/input:/app/input:rslave
```

```bash
docker run -v $(pwd)/scripts:/app/scripts:ro     # bind mount
docker run -v data_volume:/app/data               # named volume
docker run --tmpfs /app/scratch:noexec,nosuid     # tmpfs
docker run --mount type=bind,src=/mnt/nfs,dst=/app/nfs,readonly
```

## Interpreting cProfile Output

```
ncalls  tottime  percall  cumtime  percall  filename:lineno(function)
 1000    0.450    0.000    2.100    0.002   etl/transform.py:42(process_row)
    1    0.020    0.020    2.500    2.500   etl/pipeline.py:10(run)
```

- `tottime` = exclusive time in the function itself (no callees).
- `cumtime` = inclusive time including all sub-calls. High cumtime + low tottime = calls something expensive.
- `percall` = cumtime / ncalls. Values >= 0.001 warrant investigation.
- Sort by `cumtime` first to find the slowest path, then `tottime` to find expensive leaves.
- Visualise with `snakeviz profile_output.prof`.

## ETL Validation Edge Cases

| Scenario | Check | Mitigation |
|----------|-------|------------|
| Zero-row source | Row count > 0 | Fail-fast with empty-source warning |
| Duplicate PK | Uniqueness | Keep-first / keep-last / reject |
| Null in required column | NOT NULL | Reject row or apply default |
| Type coercion failure | Schema match | Cast with error on mismatch |
| Out-of-range timestamp | Date bounds | Clip or flag for review |
| Truncated CSV | Line parity | Verify footer matches header count |
| Encoding mismatch | BOM header | Reject non-UTF-8 or transcode |
| Column count mismatch | Header vs data | Strict or lenient mode per source |
