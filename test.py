import redis

r = redis.from_url(
    "rediss://default:AcmkAAIncDFkZWFjYjM5MjkyYzU0NWZiOWM4N2Y4NjY1MzNhNzlkM3AxNTE2MjA@steady-worm-51620.upstash.io:6379",
    decode_responses=True,
    ssl_cert_reqs=None
)

r.set("test", "hello")
print(r.get("test"))