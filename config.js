// The dashboard's price feed: a Cloudflare Worker that reads YCharts.
// No API keys live in this repo - the YCharts key is a secret on the Worker.
window.QUOTES_URL = 'https://ncorp-feed.austin-eck.workers.dev';
