# uiltiol

Bot that leaves and forms another bot every time it hits `!` in the code.

```bash
python3 bang_bot.py
python3 bang_bot.py some_code.py
python3 bang_bot.py --self --max-gen 3
```

On each `!` the current bot stops and a child starts at the next character. Generation is capped so a file of bangs cannot fork forever.
