# MediaInfo Share

MediaInfo Share is a small Flask application for storing MediaInfo output and giving people a link they can preview or download.

## Features

- Upload raw MediaInfo output and keep a formatted preview
- Optional expiration window for shared links
- Automatic cleanup job that removes expired entries and their files

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/AnabolicsAnonymous/mediainfo-share.git
   cd mediainfo-share
   ```

2. Copy the provided `.env.example` and fill it in. At minimum you need `SECRET_KEY` and `ENCRYPTION_KEY`. Generate values with:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"     # SECRET_KEY
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # ENCRYPTION_KEY
   ```
   Paste the results into `.env`.

4. Build and start the application:
   ```bash
   docker compose up --build -d
   ```

5. Visit the UI at `http://localhost:5000`.


## Updating

Fetch the latest code, rebuild, and restart:
```bash
git pull
docker compose up --build -d
```

## Contributing

Bug reports, feature requests, and pull requests are all welcome. Please open an issue first if you plan a larger change so we can talk through the approach.

## License

MediaInfo Share is released under the GNU Affero General Public License v3.0. See [LICENSE](LICENSE) for the full terms.

## Support

If this project saves you time, tips are appreciated:

- Bitcoin: `bc1q7nxt23ahfluesy2kxgjdkqhh7qcc3gda6wmla5`
- Ethereum / USDC: `0x24D898b1BA57BC8F5B510A841EeE8c75dcD8397d`
- Litecoin: `LL2pHmU4tYvKUCcBem3ehdrFeeuQuGbWNX`