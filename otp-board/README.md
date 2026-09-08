# PoC OTP Board (Cloudflare Email Worker)

Private page that shows DevRev/Auth0 login OTPs for `@connectadevrev.work`.
Emails still forward to `devrevpoc@gmail.com`.

```text
Login → OTP email → Email Routing → this Worker
                                      ├─ parse OTP → KV
                                      ├─ forward to Gmail
                                      └─ HTTPS page ?k=SECRET shows codes
```

## 1. Install & login

```bash
cd otp-board
npm install
npx wrangler login
```

## 2. Create KV + put the id in wrangler.toml

```bash
npm run kv:create
```

Copy the namespace **id** into `wrangler.toml`:

```toml
[[kv_namespaces]]
binding = "OTP_KV"
id = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

## 3. Set access key (secret)

```bash
openssl rand -hex 24
npm run secret:access
# paste the hex string when prompted
```

## 4. Deploy

```bash
npm run deploy
```

Note the URL, e.g. `https://connectadevrev-otp-board.<your-subdomain>.workers.dev`

Open:

```text
https://connectadevrev-otp-board.<your-subdomain>.workers.dev/?k=YOUR_ACCESS_KEY
```

## 5. Point Email Routing at the Worker

In Cloudflare → **`connectadevrev.work`** → **Email** → **Email Routing** → **Routing rules**:

For each address (`exec@`, `support-true-care@`, `support-alliancehie@`, `patient@` if any):

1. **Edit** the rule  
2. Change action from **Send to an email** → **Send to a Worker**  
3. Select worker **`connectadevrev-otp-board`**  
4. Save  

The Worker still calls `message.forward("devrevpoc@gmail.com")`, so Gmail keeps getting copies.  
`devrevpoc@gmail.com` must stay **Verified** under Destination addresses.

## 6. Test

1. Trigger a DevRev login for `exec@connectadevrev.work`  
2. Watch the OTP board page (auto-refresh every 5s)  
3. Confirm Gmail also received the mail  

## Security

- Do **not** share the URL without `?k=...`
- Rotate `ACCESS_KEY` anytime: `npm run secret:access` then redeploy if needed  
- Codes auto-expire from the board after ~10 minutes  

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Page says Unauthorized | Wrong/missing `?k=` |
| No OTPs on page, mail in Gmail | Rule still “Send to email” — switch to Worker |
| Worker error on forward | Re-verify `devrevpoc@gmail.com` destination |
| OTP not parsed | Check Worker logs: `npx wrangler tail` |
