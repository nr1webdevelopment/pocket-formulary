# Admin dashboard: setup and use

nomadceuticals.com/admin/ has two parts:

- **Inbox**: every "Report a problem" message from the website (provider pages, the footer, the OTC finder and the API docs). Each new report is also emailed to you.
- **Listings**: edit, add, verify or close the clinics and hospitals in `data/providers/`. Each save is a commit to this repository on GitHub. GitHub then rebuilds the site and Hostinger publishes it, usually within 2 minutes.

No third-party services are involved. Reports are stored on your Hostinger server in a private SQLite database. Your email address is never shown on the site.

## How it works

| Part | File | What it does |
|---|---|---|
| Report form | `scripts/report_form.py` | Dialog added to every page by the builds. It posts to `/report.php`. |
| Report endpoint | `server/report.php` | Checks the report: same website only, a hidden spam trap, and at most 5 reports per 10 minutes and 20 per day from one visitor. It saves the report and emails you. |
| Admin | `server/admin/` | `index.php` + `app.js` + `app.css` (the dashboard), `api.php` (its JSON API), `setup.php` (one-time setup), `_inc.php` (shared code, never served). |
| Private data | `nc-private/` on the server, **next to** `public_html`, never in git | `config.php` (login, GitHub token, mailbox password, settings) and `nomad.sqlite` (inbox). |

`scripts/build_public.py` copies `server/` into the root of `public/`, so the files end up at `/report.php` and `/admin/`.

Security:

- Your password is stored only as a bcrypt hash.
- Logins lock for 15 minutes after 5 wrong tries.
- Sessions use secure, HTTP-only, same-site cookies, end after 2 hours without activity, and last at most 8 hours.
- Every change needs a CSRF token.
- Admin pages are `noindex` and can't be put inside other sites (no framing).
- Visitor IP addresses are never stored, only a salted hash used for rate limits.
- Every save is checked against `schema/provider.schema.json` and the rules in `scripts/validate.py` before it goes to GitHub.
- If someone else changed the same city file since you opened it, your save is refused rather than overwriting their change.

## One-time setup (about 10 minutes)

### 1. Push this code

Push from your Mac as usual: `git push`. Wait for the GitHub Action "Build public site" to go green and Hostinger to deploy (1–2 minutes).

### 2. Check PHP on Hostinger

In hPanel → Websites → nomadceuticals.com → Advanced → **PHP Configuration**:

- Choose **PHP 8.2 or newer**.
- Make sure the extensions **pdo_sqlite**, **curl** and **mbstring** are on. They usually are.

### 3. Create a GitHub token for the admin

Go to GitHub → your avatar → Settings → Developer settings → Personal access tokens → **Fine-grained tokens** → Generate new token, and set:

- Name: `nomadceuticals-admin`
- Expiration: 1 year (set a reminder; the admin shows an error when it expires)
- Resource owner: the owner of `pocket-formulary`
- Repository access: **Only select repositories** → `pocket-formulary`
- Repository permissions: **Contents → Read and write**. Leave everything else at No access; Metadata read-only is added automatically.

Copy the token. You paste it once in the next step and never need it again.

### 4. Run setup

Open **https://nomadceuticals.com/admin/**. It sends you to the setup page. Enter:

- A username and a password of at least 12 characters (use your password manager)
- The email address where new reports should go
- The GitHub token

Setup checks that the token belongs to an account that can change the repository, so nobody else can claim your admin. It then creates the private folder `nc-private/` next to `public_html` and turns itself off.

If setup says it can't create the folder: in hPanel → **File Manager**, go one level above `public_html`, create a folder called `nc-private`, and try again.

### 5. Test

1. On the site, open any clinic and click **Report a problem**. Send a test.
2. Check that it appears in the admin inbox and that the email arrives. Check spam the first time. You can also use **Settings → Send a test email**.
3. Set up a sending mailbox (needed for reliable email). Without one, the server's basic `mail()` is used, and many inboxes drop those messages silently:
   - In hPanel → **Emails**, create a mailbox on the domain, e.g. `reports@nomadceuticals.com`. Hostinger adds the DNS records (SPF/DKIM) that let other mail servers trust it.
   - In the admin, **Settings → Email notifications**: enter that address and its password, **Save**, then **Send a test email**. If it fails, the exact reason is shown (e.g. wrong password).
   - It sends through `smtp.hostinger.com`, port 465 (SSL). Another provider's mailbox works too: change the server under "Server".

## Everyday use

- **Inbox:** reports are sorted into New / In progress / Done. Open a report to:
  - reply by email (only if the visitor gave an address)
  - jump straight to the listing it's about with **Edit listing**
  - add a private note
  - delete it
- **Listings:** pick a city, then search or filter by status. **Due for review** shows listings whose review date has passed. Click a listing to edit it.
- **Mark verified today**: after you've called the clinic or checked an official registry. It sets status, date, method, your name and a review date 90 days ahead, then publishes. It does the same as `scripts/mark_verified.py`.
- **Mark closed**: keeps the record, which shows as closed on the site.
- **Edit as JSON**: for fields the form doesn't show. It is checked the same way when you save.

### If you also edit files on your Mac

The admin and GitHub both commit to `main`, so **run `git pull` before you start working** and before you push. If a push is rejected, run `git pull` and push again.

## Password, token and email settings

- **Change password**, **replace the GitHub token** (before it expires) or change email settings: admin → **Settings**. Replacing the token asks for your admin password.
- **Forgot your password?** hPanel → File Manager → `nc-private/`: delete `config.php` (the inbox, `nomad.sqlite`, stays), then open https://nomadceuticals.com/admin/setup.php again.

## Testing locally (developers)

```bash
mkdir -p /tmp/nc-private && python3 scripts/build_public.py
cd public && NC_PRIVATE_DIR=/tmp/nc-private php -S 127.0.0.1:8000
# open http://127.0.0.1:8000/admin/ ; set NC_GITHUB_API to point at a mock to avoid real commits
```
